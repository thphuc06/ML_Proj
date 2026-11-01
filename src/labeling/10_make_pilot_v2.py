"""Pilot v2 (2026-10-23): 150 RIGHT-side crops (official rule common.right_crop), one per pano, from the 3 pilot
streets (train split). Replaces pilot v1 (75 panos x L/R). Panos come from the positions downloaded for v1
(>= 25 m apart, night dropped by brightness). Sampling stratified by PoC score terciles per street (sampling only,
never shown). Items get an opaque code (shown to annotators instead of the Mapillary id / side).
Output: data/crops/pilot_v2/<code>.jpg, data/manifest/pilot_v2.csv, sheets data/crops/pilot_v2_sheet_*.jpg."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import secrets
from datetime import date

import numpy as np
import pandas as pd
import torch
import torchvision.transforms as T
from PIL import Image, ImageDraw, ImageFont
from torchvision.models import convnext_tiny

from common import DARK, DATA, RAW_META, ROOT, RIGHT_YAW_OFF, right_crop

STREETS = ["Pasteur", "Lê Văn Sỹ", "Phan Đăng Lưu"]
PER_STREET = 50
OUT, MAN = DATA / "crops" / "pilot_v2", DATA / "manifest"
OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.RandomState(20261023)

match = pd.read_parquet(DATA / "streets" / "pano_street_match_v1.parquet").astype({"id": str})
meta = pd.read_parquet(sorted(RAW_META.glob("mapillary_pano_*.parquet"))[-1],
                       columns=["id", "compass_angle", "computed_compass_angle", "captured", "creator"]).astype({"id": str})
have = {p.stem for p in (DATA / "raw" / "pano").glob("*.jpg")}
m = match[match.street_id.isin(STREETS) & match.id.isin(have)].merge(meta, on="id")

rows, imgs = [], {}
for sid, g in m.groupby("street_id"):
    g = g.sample(frac=1, random_state=rng)
    xy = np.c_[g.lon.values * 109500, g.lat.values * 110574]
    kept = []
    for k in range(len(g)):
        if all(np.hypot(*(xy[k] - xy[q])) >= 25 for q in kept):
            kept.append(k)
    for r in g.iloc[kept].itertuples():
        e = np.asarray(Image.open(DATA / "raw" / "pano" / f"{r.id}.jpg").convert("RGB"))
        bright = float(e[: e.shape[0] // 2].mean())
        if bright < DARK:
            continue
        ca = r.computed_compass_angle if r.computed_compass_angle == r.computed_compass_angle else r.compass_angle
        img, yaw = right_crop(e, r.travel_bearing, ca)
        imgs[r.id] = img
        rows.append({**r._asdict(), "compass": ca, "yaw": yaw, "brightness": round(bright)})
pos = pd.DataFrame(rows)
print("day positions per street:", pos.street_id.value_counts().to_dict())

ck = torch.load(ROOT / "models" / "poc" / "convnext_h1.pt", map_location="cpu")
net = convnext_tiny()
net.classifier[2] = torch.nn.Linear(net.classifier[2].in_features, 3)
net.load_state_dict(ck["state_dict"])
net = net.cuda().eval()
tf = T.Compose([T.Resize((ck["size"], ck["size"])), T.ToTensor(), T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
with torch.no_grad():
    pos["score"] = np.concatenate([torch.softmax(net(torch.stack([tf(Image.fromarray(imgs[i])) for i in pos.id[s:s + 32]]).cuda()).float(), 1)[:, 2].cpu().numpy()
                                   for s in range(0, len(pos), 32)])

pick = []
for sid, g in pos.groupby("street_id"):
    g = g.assign(stratum=pd.qcut(g.score.rank(method="first"), 3, labels=["low", "mid", "high"]))
    n = dict(zip(["high", "mid", "low"], [17, 17, 16]))
    pick += [x.sample(min(n[s], len(x)), random_state=rng) for s, x in g.groupby("stratum", observed=True)]
pick = pd.concat(pick)
if len(pick) < 3 * PER_STREET:  # top up from leftovers if a stratum was short
    rest = pos[~pos.id.isin(pick.id)]
    pick = pd.concat([pick, rest.sample(3 * PER_STREET - len(pick), random_state=rng)])
pick = pick.sample(frac=1, random_state=rng).reset_index(drop=True)
pick["item"] = [secrets.token_hex(4) for _ in range(len(pick))]
for r in pick.itertuples():
    Image.fromarray(imgs[r.id]).save(OUT / f"{r.item}.jpg", quality=90)
man = pd.DataFrame({
    "item": pick.item, "file": "pilot_v2/" + pick.item + ".jpg", "parent_pano_id": pick.id, "side": "R",
    "yaw_off_from_travel": RIGHT_YAW_OFF, "street_id": pick.street_id, "split": "train", "lat": pick.lat, "lon": pick.lon,
    "captured_at": pick.captured, "creator": pick.creator, "sequence": pick.sequence, "travel_bearing": pick.travel_bearing.round(1),
    "yaw": pick.yaw, "brightness": pick.brightness, "dist_to_street_m": pick.dist_m.round(1), "source": "mapillary",
    "licence": "CC BY-SA 4.0", "mapillary_url": "https://www.mapillary.com/app/?pKey=" + pick.id, "phase": "pilot",
    "sampling_stratum": pick.stratum.astype(str), "poc_p_blocked_sampling_only": pick.score.round(3)})
man.to_csv(MAN / "pilot_v2.csv", index=False, encoding="utf-8-sig")

font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 14)
W = 240
for s in range(0, len(man), 50):
    part = man.iloc[s:s + 50]
    sheet = Image.new("RGB", (W * 10, W * 5), "white")
    for k, r in enumerate(part.itertuples()):
        im = Image.open(OUT / f"{r.item}.jpg").resize((W, W))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, W, 17), fill=(0, 0, 0))
        d.text((3, 1), f"#{s + k} {r.street_id[:10]} b{r.brightness}", fill=(255, 255, 0), font=font)
        sheet.paste(im, ((k % 10) * W, (k // 10) * W))
    sheet.save(DATA / "crops" / f"pilot_v2_sheet_{s // 50}.jpg", quality=85)
with open(ROOT / "docs" / "collection_log.md", "a", encoding="utf-8") as f:
    f.write(f"\n## {date.today()} — Pilot v2 (`src/10_make_pilot_v2.py`)\n"
            f"- Replaces pilot v1 (L+R). 150 right-side crops, one per pano, yaw {RIGHT_YAW_OFF} deg from travel, pitch -4, FOV 90.\n"
            f"- Streets {', '.join(STREETS)}: {man.street_id.value_counts().to_dict()}; strata by PoC score terciles (sampling only).\n"
            f"- Opaque item codes shown to annotators; mapping to Mapillary ids in data/manifest/pilot_v2.csv.\n")
print("pilot v2:", len(man), man.street_id.value_counts().to_dict(), man.sampling_stratum.value_counts().to_dict())
