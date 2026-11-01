"""Exploratory: should we keep only right-side crops? (decision aid; the pilot's human labels are the final evidence)

A. Visibility of the near sidewalk, L vs R, on every downloaded pano (street preview + pilot):
   SegFormer-B5 (Cityscapes) on each crop; in the bottom band (rows 55-100%, where the near sidewalk sits):
   - sw_band: sidewalk share; road_band: road share
   - near_visible = sw_band >= 0.10 and road_band < 0.60 (bottom band is mostly sidewalk-ish, not roadway)
   Parked motorbikes on a blocked sidewalk reduce sidewalk pixels, so near_visible also counts
   sidewalk+motorcycle+bicycle+person in the band when road_band < 0.40 (blocked sidewalks must not look "invisible").
B. Coverage with right-only crops on the 12 draft main streets: share of 25 m positions that have passes in both
   travel directions (the opposite pass's right crop shows the other sidewalk), and one-way / dual-carriageway flags.
Outputs: data/streets/side_analysis_crops.csv, data/streets/side_coverage.csv, printed summary, sample sheets."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import json
import re
from collections import defaultdict

import numpy as np
import pandas as pd
import torch
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString
from shapely.ops import unary_union
from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

from common import DATA, RAW_META, RAW_OSM, axis_diff, bearing_xy, side_crops, to_xy

ST = DATA / "streets"
MAIN = ["Hải Thượng Lãn Ông", "Nơ Trang Long", "Nguyễn Kiệm#0", "Võ Văn Tần", "Hồng Bàng", "Cách Mạng Tháng Tám#0", "Trần Phú",
        "Nguyễn Thị Minh Khai", "Nguyễn Trãi", "Hai Bà Trưng", "Nguyễn Đình Chiểu#0", "Lý Thường Kiệt"]

# ---------------- A. visibility
prev = pd.read_csv(ST / "street_preview_crops_v1.csv", dtype={"id": str})[["id", "street_id", "brightness"]].drop_duplicates("id")
pil = pd.read_csv(DATA / "manifest" / "pilot_v1.csv", dtype={"parent_pano_id": str})
pil = pil.rename(columns={"parent_pano_id": "id"})[["id", "street_id", "brightness"]].drop_duplicates("id")
panos = pd.concat([prev, pil]).drop_duplicates("id")
panos = panos[panos.brightness >= 90]
match = pd.read_parquet(ST / "pano_street_match_v1.parquet").astype({"id": str})
meta = pd.read_parquet(sorted(RAW_META.glob("mapillary_pano_*.parquet"))[-1], columns=["id", "compass_angle", "computed_compass_angle"]).astype({"id": str})
panos = panos.merge(match[["id", "travel_bearing"]], on="id").merge(meta, on="id")
print("daytime panos analysed:", len(panos), "| streets:", panos.street_id.nunique())

proc = SegformerImageProcessor.from_pretrained("nvidia/segformer-b5-finetuned-cityscapes-1024-1024")
net = SegformerForSemanticSegmentation.from_pretrained("nvidia/segformer-b5-finetuned-cityscapes-1024-1024").cuda().eval().half()
ROAD, SW, PERSON, MOTO, BIKE = 0, 1, 11, 17, 18
rows, crops = [], {}
batch, keys = [], []


def flush():
    with torch.no_grad():
        inp = proc(images=batch, return_tensors="pt").to("cuda")
        logits = net(pixel_values=inp["pixel_values"].half()).logits
        seg = torch.nn.functional.interpolate(logits.float(), size=(512, 512), mode="bilinear").argmax(1).cpu().numpy()
    for (iid, side), m in zip(keys, seg):
        band = m[int(0.55 * 512):]
        f = lambda c: float(np.isin(band, c).mean())  # noqa: E731
        rows.append({"id": iid, "side": side, "sw_band": f([SW]), "road_band": f([ROAD]),
                     "swlike_band": f([SW, PERSON, MOTO, BIKE]), "sw_full": float((m == SW).mean())})
    batch.clear()
    keys.clear()


for r in panos.itertuples():
    e = np.asarray(Image.open(DATA / "raw" / "pano" / f"{r.id}.jpg").convert("RGB"))
    ca = r.computed_compass_angle if r.computed_compass_angle == r.computed_compass_angle else r.compass_angle
    for side, (img, _) in side_crops(e, r.travel_bearing, ca).items():
        im = Image.fromarray(img).resize((512, 512))
        batch.append(im)
        keys.append((r.id, side))
        if len(crops) < 4000:
            crops[(r.id, side)] = im.resize((200, 200))
    if len(batch) >= 16:
        flush()
if batch:
    flush()
c = pd.DataFrame(rows).merge(panos[["id", "street_id"]], on="id")
c["near_visible"] = ((c.sw_band >= 0.10) & (c.road_band < 0.60)) | ((c.swlike_band >= 0.15) & (c.road_band < 0.40))
c.to_csv(ST / "side_analysis_crops.csv", index=False, encoding="utf-8-sig")

print("\n== A. near-sidewalk visibility by side (all streets)")
print(c.groupby("side").agg(n=("id", "size"), near_visible=("near_visible", "mean"), sw_band_median=("sw_band", "median"),
                            road_band_median=("road_band", "median")).round(2).to_string())
both = c.pivot(index="id", columns="side", values="near_visible").dropna()
print(f"panos where: both visible {(both.L & both.R).mean():.0%} | only R {(~both.L & both.R).mean():.0%} | "
      f"only L {(both.L & ~both.R).mean():.0%} | neither {(~both.L & ~both.R).mean():.0%}")

# street attributes from OSM: one-way share and dual carriageway (two parallel same-name ways)
ways = json.load(open(RAW_OSM / "roads.json", encoding="utf-8"))["elements"]
norm = lambda n: re.sub(r"\s+", " ", re.sub(r"^(Đường|Duong|Phố)\s+", "", n.strip(), flags=re.I))  # noqa: E731
by = defaultdict(list)
for w in ways:
    by[norm(w["tags"]["name"])].append(w)
attr = {}
for sid in c.street_id.unique():
    ws = by.get(sid.split("#")[0], [])
    lines = [LineString([to_xy(p["lon"], p["lat"]) for p in w["geometry"]]) for w in ws]
    if not lines:
        continue
    L = sum(l.length for l in lines)
    center = unary_union(lines).buffer(20).area / 40
    attr[sid] = {"oneway": sum(l.length for l, w in zip(lines, ws) if w["tags"].get("oneway") == "yes") / L > 0.5,
                 "dual": L / center > 1.5, "lanes": pd.Series([w["tags"].get("lanes") for w in ws]).dropna().astype(str).mode().tolist()[:1]}
a = pd.DataFrame(attr).T
c = c.merge(a, left_on="street_id", right_index=True, how="left")
c["type"] = np.where(c.dual == True, "dual carriageway", np.where(c.oneway == True, "one-way", "two-way undivided"))  # noqa: E712
print("\n== A2. near-sidewalk visible by street type and side")
print(c.pivot_table(index="type", columns="side", values="near_visible", aggfunc="mean").round(2).join(
    c.groupby("type").id.nunique().rename("panos")).to_string())
per = c.pivot_table(index="street_id", columns="side", values="near_visible", aggfunc="mean").round(2)
per = per.join(a[["oneway", "dual"]]).sort_values("L")
print("\n== A3. per street (lowest L first)\n" + per.to_string())

# ---------------- B. coverage of both sidewalks with right-only crops, 12 main streets
streets_axis = {}
for sid in MAIN:
    ws = by.get(sid.split("#")[0], [])
    streets_axis[sid] = [(LineString([to_xy(p["lon"], p["lat"]) for p in w["geometry"]])) for w in ws]
mm = match[match.street_id.isin(MAIN)].copy()
mm["x"], mm["y"] = to_xy(mm.lon.values, mm.lat.values)
cov = []
for sid, g in mm.groupby("street_id"):
    segs = [s for l in streets_axis[sid] for s in zip(list(l.coords)[:-1], list(l.coords)[1:])]
    segx = np.array([[(a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2, bearing_xy(*a_, *b_)] for a_, b_ in segs])
    # direction sign relative to the nearest segment's drawing direction: +1 along, -1 against
    d = np.hypot(g.x.values[:, None] - segx[None, :, 0], g.y.values[:, None] - segx[None, :, 1])
    ax = segx[d.argmin(1), 2]
    diff = np.abs((g.travel_bearing.values - ax + 180) % 360 - 180)
    g = g.assign(dirn=np.where(diff < 90, 1, -1))
    xy = g[["x", "y"]].values
    kept = []
    for k in np.random.RandomState(0).permutation(len(g)):
        if all(np.hypot(*(xy[k] - xy[q])) >= 25 for q in kept):
            kept.append(k)
    near = [set(g.dirn.values[np.hypot(*(xy - xy[k]).T) <= 15]) for k in kept]
    cov.append({"street_id": sid, "positions": len(kept), "both_directions": np.mean([len(s) == 2 for s in near]),
                "oneway": attr.get(sid, {}).get("oneway"), "dual": attr.get(sid, {}).get("dual")})
cov = pd.DataFrame(cov).round(2)
cov.to_csv(ST / "side_coverage.csv", index=False, encoding="utf-8-sig")
print("\n== B. right-only coverage: share of 25 m positions with passes in BOTH directions (12 main streets)")
print(cov.to_string(index=False))

# sample sheets for eyeballing: 24 random panos, L | R side by side
font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 14)
smp = both.sample(24, random_state=3).index
sheet = Image.new("RGB", (200 * 8, 200 * 6), "white")
for k, iid in enumerate(smp):
    for j, side in enumerate("LR"):
        im = crops[(iid, side)].copy()
        r = c[(c.id == iid) & (c.side == side)].iloc[0]
        ImageDraw.Draw(im).rectangle((0, 0, 200, 18), fill=(0, 0, 0))
        ImageDraw.Draw(im).text((3, 1), f"{side} vis={int(r.near_visible)} sw{r.sw_band:.2f} rd{r.road_band:.2f}", fill=(255, 255, 0), font=font)
        sheet.paste(im, (((2 * k + j) % 8) * 200, ((2 * k + j) // 8) * 200))
sheet.save(ST / "side_analysis_sample.jpg", quality=85)
