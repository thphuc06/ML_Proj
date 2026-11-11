"""Shared helpers for train enrichment (docs/data_enrichment.md): rebuild crops from Mapillary panos, frozen image
embeddings, and the selector (logistic regression on embeddings). Selector scores choose which crops people label;
they are never labels. Used by src/analysis/21_selector_benchmark.py and src/collection/22_collect_train_extra.py."""
import os
import threading
from collections import defaultdict

import numpy as np
import requests
from PIL import Image

from common import CROP_FOV, CROP_PITCH, CROP_PX, DATA, env

PANO = DATA / "raw" / "pano"
EMB = DATA / "raw" / "embeddings"
ENCODERS = {  # name -> (Hugging Face id, kind)
    "clip_b16": ("openai/clip-vit-base-patch16", "clip"),
    "clip_l14": ("openai/clip-vit-large-patch14", "clip"),
    "dinov2_b14": ("facebook/dinov2-base", "dino"),
    "siglip_b16": ("google/siglip-base-patch16-224", "clip"),
}
_locks, _session = defaultdict(threading.Lock), []


def session():
    if not _session:
        s = requests.Session()
        s.headers["Authorization"] = f"OAuth {env('MAPILLARY_TOKEN')}"
        _session.append(s)
    return _session[0]


def fetch_pano(pid, keep=True):
    """Equirectangular pano (2048 px thumb) as uint8 array, or None. keep=True caches it in data/raw/pano."""
    p = PANO / f"{pid}.jpg"
    with _locks[pid]:
        if p.exists():
            return np.asarray(Image.open(p).convert("RGB"))
        for _ in range(3):
            try:
                url = session().get(f"https://graph.mapillary.com/{pid}", params={"fields": "thumb_2048_url"}, timeout=30).json()["thumb_2048_url"]
                raw = requests.get(url, timeout=60).content
                if keep:
                    PANO.mkdir(parents=True, exist_ok=True)
                    tmp = p.with_suffix(".part")
                    tmp.write_bytes(raw)
                    os.replace(tmp, p)
                import io
                return np.asarray(Image.open(io.BytesIO(raw)).convert("RGB"))
            except Exception:  # noqa: BLE001
                pass
    return None


def crop_at_yaw(equi, yaw):
    """The dataset crop for a manifest row: same projection as common.right_crop, yaw taken from the manifest."""
    import py360convert
    return py360convert.e2p(equi, fov_deg=CROP_FOV, u_deg=yaw, v_deg=CROP_PITCH, out_hw=(CROP_PX, CROP_PX)).astype(np.uint8)


def embed(name, paths, batch=32, log=None):
    """L2-normalised image embeddings (n x d, float32) of a frozen encoder. CLIP/SigLIP: projected image feature.
    DINOv2: CLS token concatenated with the mean patch token (the linear-probe input of Oquab et al. 2023)."""
    import torch
    from transformers import AutoImageProcessor, AutoModel
    hf, kind = ENCODERS[name]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    proc, net = AutoImageProcessor.from_pretrained(hf), AutoModel.from_pretrained(hf).to(dev).eval()
    out = []
    with torch.no_grad():
        for s in range(0, len(paths), batch):
            x = proc(images=[Image.open(p).convert("RGB") for p in paths[s:s + batch]], return_tensors="pt")["pixel_values"].to(dev)
            if kind == "clip":
                f = net.get_image_features(pixel_values=x)
                f = f if torch.is_tensor(f) else f.pooler_output
            else:
                h = net(pixel_values=x).last_hidden_state
                f = torch.cat([h[:, 0], h[:, 1:].mean(1)], dim=1)
            out.append(torch.nn.functional.normalize(f.float(), dim=1).cpu().numpy())
            if log and (s // batch) % 10 == 0:
                log(f"{name} {s + len(paths[s:s + batch])}/{len(paths)}")
    return np.concatenate(out).astype(np.float32)


def cached_embed(name, items, paths, log=None):
    """embed() with a per-encoder cache keyed by item code (data/raw/embeddings/<name>.npz, not in git)."""
    EMB.mkdir(parents=True, exist_ok=True)
    f = EMB / f"{name}.npz"
    have = dict(zip(*(lambda z: (z["items"], z["emb"]))(np.load(f, allow_pickle=False)))) if f.exists() else {}
    todo = [(i, p) for i, p in zip(items, paths) if i not in have]
    if todo:
        new = embed(name, [p for _, p in todo], log=log)
        have.update({i: e for (i, _), e in zip(todo, new)})
        np.savez(f, items=np.array(list(have)), emb=np.stack(list(have.values())))
    return np.stack([have[i] for i in items])


def text_embed(name, prompts):
    import torch
    from transformers import AutoModel, AutoTokenizer
    hf, _ = ENCODERS[name]
    tok, net = AutoTokenizer.from_pretrained(hf), AutoModel.from_pretrained(hf).eval()
    with torch.no_grad():
        f = net.get_text_features(**tok(prompts, padding="max_length" if "siglip" in name else True, return_tensors="pt"))
        f = f if torch.is_tensor(f) else f.pooler_output
    return torch.nn.functional.normalize(f.float(), dim=1).numpy()


CS = (0.001, 0.01, 0.1, 1.0)


def fit_selector(X, y, groups=None, C=None):
    """Logistic regression P(blocked) on standardised embeddings. y = 1 for 'Bị chặn', 0 for everything else that a
    person labelled (clear AND not-enough-information), so the score is the expected yield of labelling the crop.
    C is picked by average precision over 3 street-grouped folds (groups = street of each row) unless given.
    Returns (fitted pipeline, C)."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    def make(c):
        return make_pipeline(StandardScaler(), LogisticRegression(C=c, class_weight="balanced", max_iter=3000))
    if C is None:
        ap = {c: np.mean([average_precision_score(y[te], make(c).fit(X[tr], y[tr]).predict_proba(X[te])[:, 1])
                          for tr, te in GroupKFold(3).split(X, y, groups)]) for c in CS}
        C = max(ap, key=ap.get)
    return make(C).fit(X, y), C
