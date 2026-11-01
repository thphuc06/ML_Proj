"""Step 1d: visual + rough-model preview of candidate streets (street SELECTION aid only).
Nothing here is a label or a dataset filter: the PoC model was trained on AI-made labels and Mask2Former is used
only to estimate what share of a street's crops show a sidewalk.
Per street (est_usable_crops >= MIN_CROPS): N panos at distinct >= 25 m positions, spread along the street ->
download thumb_2048 -> brightness (night check) -> left/right 90-deg crops perpendicular to travel ->
  - sidewalk_visible: Mask2Former (Mapillary Vistas) sidewalk+curb >= 3% of the crop
  - poc_blocked: PoC ConvNeXt P(khong_di_duoc) on daytime crops with visible sidewalk
Outputs: data/streets/preview/<street>.jpg contact sheets, data/streets/street_preview_v1.csv."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import concurrent.futures as cf
import re
import sys

import numpy as np
import pandas as pd
import py360convert
import requests
import torch
import torchvision.transforms as T
from PIL import Image, ImageDraw, ImageFont
from torchvision.models import convnext_tiny
from transformers import AutoProcessor, Mask2FormerForUniversalSegmentation

from common import DATA, RAW_META, ROOT, env

N, MIN_CROPS, DARK = 20, 100, 70
ST = DATA / "streets"
PANO = DATA / "raw" / "pano"
PREV = ST / "preview"
for d in (PANO, PREV):
    d.mkdir(parents=True, exist_ok=True)
S = requests.Session()
S.headers["Authorization"] = f"OAuth {env('MAPILLARY_TOKEN')}"

cand = pd.read_csv(ST / "street_candidates_v1.csv")
cand = cand[cand.est_usable_crops >= MIN_CROPS]
match = pd.read_parquet(ST / "pano_street_match_v1.parquet")
meta = pd.read_parquet(sorted(RAW_META.glob("mapillary_pano_*.parquet"))[-1], columns=["id", "compass_angle", "computed_compass_angle", "captured", "creator"])
match = match[match.street_id.isin(cand.street_id)].merge(meta, on="id")

pick = []
for sid, g in match.groupby("street_id"):
    g = g.sample(frac=1, random_state=0)
    xy = np.c_[g.lon.values * 109500, g.lat.values * 110574]
    kept = []
    for k in range(len(g)):
        if all(np.hypot(*(xy[k] - xy[q])) >= 25 for q in kept):
            kept.append(k)
    kept = g.iloc[kept].sort_values(["lon", "lat"])
    pick.append(kept.iloc[np.linspace(0, len(kept) - 1, min(N, len(kept))).astype(int)])
pick = pd.concat(pick).reset_index(drop=True)
print("streets", pick.street_id.nunique(), "| panos", len(pick))


def fetch(iid):
    p = PANO / f"{iid}.jpg"
    if not p.exists():
        for _ in range(3):
            try:
                url = S.get(f"https://graph.mapillary.com/{iid}", params={"fields": "thumb_2048_url"}, timeout=30).json()["thumb_2048_url"]
                p.write_bytes(requests.get(url, timeout=60).content)
                break
            except Exception:  # noqa: BLE001
                pass
    return p.exists()


with cf.ThreadPoolExecutor(8) as ex:
    pick["ok"] = list(ex.map(fetch, pick.id))
pick = pick[pick.ok]


def norm(a):
    return (a + 180) % 360 - 180


crops, rows = [], []
for r in pick.itertuples():
    e = np.asarray(Image.open(PANO / f"{r.id}.jpg").convert("RGB"))
    bright = float(e[: e.shape[0] // 2].mean())
    ca = r.computed_compass_angle if r.computed_compass_angle == r.computed_compass_angle else r.compass_angle
    for side, off in (("L", -90), ("R", 90)):
        yaw = norm(r.travel_bearing + off - ca)
        crops.append(Image.fromarray(py360convert.e2p(e, fov_deg=90, u_deg=yaw, v_deg=-4, out_hw=(640, 640)).astype(np.uint8)))
        rows.append({"street_id": r.street_id, "id": r.id, "side": side, "brightness": round(bright), "captured": r.captured})
cr = pd.DataFrame(rows)
print("crops", len(cr))

# sidewalk visibility (Mask2Former) and rough PoC blocked probability, GPU
dev = "cuda"
mid = "facebook/mask2former-swin-large-mapillary-vistas-semantic"
proc = AutoProcessor.from_pretrained(mid)
seg = Mask2FormerForUniversalSegmentation.from_pretrained(mid).to(dev).eval().half()
names = [seg.config.id2label[i] for i in range(len(seg.config.id2label))]
sw_ids = [names.index("Sidewalk"), names.index("Curb")]
sw = []
with torch.no_grad():
    for s in range(0, len(crops), 8):
        ims = [c.resize((512, 512)) for c in crops[s:s + 8]]
        inp = proc(images=ims, return_tensors="pt").to(dev)
        inp["pixel_values"] = inp["pixel_values"].half()
        for m_ in proc.post_process_semantic_segmentation(seg(**inp), target_sizes=[(512, 512)] * len(ims)):
            sw.append(float(torch.isin(m_, torch.tensor(sw_ids, device=m_.device)).float().mean()))
cr["sidewalk_frac"] = np.round(sw, 3)
del seg
torch.cuda.empty_cache()

ck = torch.load(ROOT / "models" / "poc" / "convnext_h1.pt", map_location="cpu")
net = convnext_tiny()
net.classifier[2] = torch.nn.Linear(net.classifier[2].in_features, 3)
net.load_state_dict(ck["state_dict"])
net = net.to(dev).eval()
tf = T.Compose([T.Resize((ck["size"], ck["size"])), T.ToTensor(), T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
P = []
with torch.no_grad():
    for s in range(0, len(crops), 32):
        P.append(torch.softmax(net(torch.stack([tf(c) for c in crops[s:s + 32]]).to(dev)).float(), 1).cpu().numpy())
P = np.concatenate(P)
cr["p_partial"], cr["p_blocked"] = P[:, 1].round(3), P[:, 2].round(3)
cr.to_csv(ST / "street_preview_crops_v1.csv", index=False)

# contact sheets: one row per pano (L | R), label with brightness / sidewalk / PoC p_blocked
font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 15)
W = 220
for sid, g in cr.groupby("street_id", sort=False):
    idx = g.index.tolist()
    cols = 8
    sheet = Image.new("RGB", (W * cols, W * int(np.ceil(len(idx) / cols))), "white")
    for k, i in enumerate(idx):
        im = crops[i].resize((W, W))
        d = ImageDraw.Draw(im)
        r = cr.loc[i]
        d.rectangle((0, 0, W, 20), fill=(0, 0, 0))
        d.text((4, 1), f"{r.side} b{r.brightness} sw{r.sidewalk_frac:.2f} pB{r.p_blocked:.2f}", fill=(255, 255, 0), font=font)
        sheet.paste(im, ((k % cols) * W, (k // cols) * W))
    sheet.save(PREV / f"{re.sub(r'[^0-9A-Za-zÀ-ỹ#]+', '_', sid)}.jpg", quality=85)

day = cr.brightness >= DARK
vis = cr.sidewalk_frac >= 0.03
summ = cr.groupby("street_id").agg(
    crops=("id", "size"), night_share=("brightness", lambda b: round(float((b < DARK).mean()), 2)),
    sidewalk_visible=("sidewalk_frac", lambda v: round(float((v >= 0.03).mean()), 2)))
ev = cr[day & vis].groupby("street_id").agg(n_eval=("id", "size"), poc_blocked=("p_blocked", "mean"),
                                            poc_blocked_share=("p_blocked", lambda p: (p >= 0.5).mean()))
summ = summ.join(ev).round(2)
out = cand.merge(summ, left_on="street_id", right_index=True, how="left")
out.to_csv(ST / "street_preview_v1.csv", index=False, encoding="utf-8-sig")
pd.set_option("display.width", 250, "display.max_rows", 100)
print(out[["street_id", "est_usable_crops", "commerce_per_km", "crops", "night_share", "sidewalk_visible", "n_eval", "poc_blocked", "poc_blocked_share"]]
      .sort_values("poc_blocked_share", ascending=False).to_string(index=False))
