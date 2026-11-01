"""Exploratory: which right-side view shows the near sidewalk best? (decides the crop rule before full collection)
Variants: yaw offset from travel direction {60, 75, 90} deg x pitch {-4, -10} deg, FOV 90, 640 px.
Metric (SegFormer-B5 Cityscapes, 512 px): in the bottom band (rows 55-100%) share of sidewalk, of sidewalk-like
(sidewalk + person + motorcycle + bicycle: parked bikes on a blocked sidewalk are still 'sidewalk area') and of road;
whole-image sidewalk share as 'how much sidewalk length is in view'. 400 random daytime panos (preview + pilot).
Outputs: data/streets/crop_param_study.csv + sheet data/streets/crop_param_sheet.jpg (8 panos x 6 variants)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import numpy as np
import pandas as pd
import py360convert
import torch
from PIL import Image, ImageDraw, ImageFont
from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

from common import DATA, RAW_META

ST = DATA / "streets"
VARIANTS = [(y, p) for y in (60, 75, 90) for p in (-4, -10)]
c = pd.read_csv(ST / "side_analysis_crops.csv", dtype={"id": str})
ids = c.id.drop_duplicates().sample(400, random_state=11)
match = pd.read_parquet(ST / "pano_street_match_v1.parquet").astype({"id": str})
meta = pd.read_parquet(sorted(RAW_META.glob("mapillary_pano_*.parquet"))[-1], columns=["id", "compass_angle", "computed_compass_angle"]).astype({"id": str})
P = match[match.id.isin(ids)][["id", "travel_bearing"]].merge(meta, on="id").drop_duplicates("id")

proc = SegformerImageProcessor.from_pretrained("nvidia/segformer-b5-finetuned-cityscapes-1024-1024")
net = SegformerForSemanticSegmentation.from_pretrained("nvidia/segformer-b5-finetuned-cityscapes-1024-1024").cuda().eval().half()
rows, keep, batch, keys = [], {}, [], []
sheet_ids = P.id.iloc[:8].tolist()


def flush():
    with torch.no_grad():
        inp = proc(images=batch, return_tensors="pt").to("cuda")
        lg = net(pixel_values=inp["pixel_values"].half()).logits
        seg = torch.nn.functional.interpolate(lg.float(), size=(512, 512), mode="bilinear").argmax(1).cpu().numpy()
    for (iid, y, p), m in zip(keys, seg):
        band = m[int(0.55 * 512):]
        rows.append({"id": iid, "yaw_off": y, "pitch": p, "sw_band": float((band == 1).mean()), "road_band": float((band == 0).mean()),
                     "swlike_band": float(np.isin(band, [1, 11, 17, 18]).mean()), "sw_full": float((m == 1).mean())})
    batch.clear()
    keys.clear()


for r in P.itertuples():
    e = np.asarray(Image.open(DATA / "raw" / "pano" / f"{r.id}.jpg").convert("RGB"))
    ca = r.computed_compass_angle if r.computed_compass_angle == r.computed_compass_angle else r.compass_angle
    for y, p in VARIANTS:
        yaw = (r.travel_bearing + y - ca + 180) % 360 - 180
        im = Image.fromarray(py360convert.e2p(e, fov_deg=90, u_deg=yaw, v_deg=p, out_hw=(512, 512)).astype(np.uint8))
        batch.append(im)
        keys.append((r.id, y, p))
        if r.id in sheet_ids:
            keep[(r.id, y, p)] = im.resize((220, 220))
    if len(batch) >= 24:
        flush()
if batch:
    flush()
d = pd.DataFrame(rows)
d["near_visible"] = ((d.sw_band >= 0.10) & (d.road_band < 0.60)) | ((d.swlike_band >= 0.15) & (d.road_band < 0.40))
d.to_csv(ST / "crop_param_study.csv", index=False)
print(f"panos {d.id.nunique()}")
print(d.groupby(["yaw_off", "pitch"]).agg(near_visible=("near_visible", "mean"), sw_band=("sw_band", "mean"), swlike_band=("swlike_band", "mean"),
                                         road_band=("road_band", "mean"), sw_full=("sw_full", "mean")).round(3).to_string())
best = d.loc[d.groupby("id").swlike_band.idxmax()].groupby(["yaw_off", "pitch"]).size()
print("\nvariant with max sidewalk-like share per pano:\n" + best.to_string())

font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 14)
sheet = Image.new("RGB", (220 * 6, 220 * 8), "white")
for i, iid in enumerate(sheet_ids):
    for j, (y, p) in enumerate(VARIANTS):
        im = keep[(iid, y, p)].copy()
        ImageDraw.Draw(im).rectangle((0, 0, 220, 18), fill=(0, 0, 0))
        ImageDraw.Draw(im).text((3, 1), f"yaw+{y} pitch{p}", fill=(255, 255, 0), font=font)
        sheet.paste(im, (j * 220, i * 220))
sheet.save(ST / "crop_param_sheet.jpg", quality=85)
