"""Step 2 (main collection): right-side crops for the street list in configs/streets_v1.yaml. Runs on the server (CPU).
Per street: matched panos (03_rank_streets) -> positions = greedy thinning >= 25 m -> per position up to 2 panos
from DISTINCT capture days (different sequences preferred); all panos within a position share `position_group`
(kept in one split; with street splits this is automatic) -> positions already used by the pilot are skipped ->
cap per street (random positions) -> download thumb_2048 -> drop night (brightness < DARK) -> common.right_crop ->
drop exact-duplicate crops (md5). Opaque item codes; manifest keeps provenance.
Usage: python 11_collect_main.py [--dry]  (dry = counts only, no download)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import concurrent.futures as cf
import hashlib
import re
import secrets
import sys
from datetime import date

import numpy as np
import pandas as pd
import requests
from PIL import Image

from common import DARK, DATA, RAW_META, RIGHT_YAW_OFF, ROOT, env, right_crop

DRY = "--dry" in sys.argv
CFG = (ROOT / "configs" / "streets_v1.yaml").read_text(encoding="utf-8")
CAP = int(re.search(r"cap_r_crops_per_street:\s*(\d+)", CFG).group(1))
STREETS = {m.group(1): m.group(2) for m in re.finditer(r'id:\s*"([^"]+)",\s*split:\s*(\w+)', CFG)}
PANO, OUT, MAN = DATA / "raw" / "pano", DATA / "crops" / "main", DATA / "manifest"
for d in (PANO, OUT, MAN):
    d.mkdir(parents=True, exist_ok=True)
rng = np.random.RandomState(20261023)
S = requests.Session()
S.headers["Authorization"] = f"OAuth {env('MAPILLARY_TOKEN')}"

match = pd.read_parquet(DATA / "streets" / "pano_street_match_v1.parquet").astype({"id": str})
meta = pd.read_parquet(sorted(RAW_META.glob("mapillary_pano_*.parquet"))[-1],
                       columns=["id", "compass_angle", "computed_compass_angle", "captured", "creator"]).astype({"id": str})
pilot = pd.read_csv(MAN / "pilot_v2.csv", dtype={"parent_pano_id": str})
m = match[match.street_id.isin(STREETS)].merge(meta, on="id")
m["day"] = m.captured.dt.date
m["x"], m["y"] = m.lon.values * 109500, m.lat.values * 110574
px, py = pilot.lon.values * 109500, pilot.lat.values * 110574

sel = []
for sid, g in m.groupby("street_id"):
    g = g.sample(frac=1, random_state=rng).reset_index(drop=True)
    xy = g[["x", "y"]].values
    centres = []
    for k in range(len(g)):
        if all(np.hypot(*(xy[k] - xy[q])) >= 25 for q in centres):
            centres.append(k)
    pos = []
    for gi, k in enumerate(centres):
        if len(px) and np.hypot(px - xy[k][0], py - xy[k][1]).min() < 15:
            continue  # pilot already covers this position
        near = g[np.hypot(*(xy - xy[k]).T) <= 15]
        near = near.sort_values("sequence").drop_duplicates("day")  # one pano per capture day
        pos.append(near.sample(min(2, len(near)), random_state=rng).assign(position_group=f"{sid}|{gi}"))
    rng.shuffle(pos)
    taken, n = [], 0
    for p in pos:
        if n + len(p) > CAP:
            break
        taken.append(p)
        n += len(p)
    sel.append(pd.concat(taken).assign(split=STREETS[sid]))
sel = pd.concat(sel).drop_duplicates("id").reset_index(drop=True)
print("selected panos:", len(sel), "| by split:", sel.split.value_counts().to_dict())
print(sel.groupby("street_id").agg(panos=("id", "size"), positions=("position_group", "nunique"), split=("split", "first")).to_string())
if DRY:
    raise SystemExit


def work(r):
    p = PANO / f"{r.id}.jpg"
    for _ in range(3):
        if p.exists():
            break
        try:
            url = S.get(f"https://graph.mapillary.com/{r.id}", params={"fields": "thumb_2048_url"}, timeout=30).json()["thumb_2048_url"]
            p.write_bytes(requests.get(url, timeout=60).content)
        except Exception:  # noqa: BLE001
            pass
    if not p.exists():
        return {"id": r.id, "status": "download_failed"}
    e = np.asarray(Image.open(p).convert("RGB"))
    bright = float(e[: e.shape[0] // 2].mean())
    if bright < DARK:
        return {"id": r.id, "status": "night", "brightness": round(bright)}
    ca = r.computed_compass_angle if r.computed_compass_angle == r.computed_compass_angle else r.compass_angle
    img, yaw = right_crop(e, r.travel_bearing, ca)
    item = secrets.token_hex(4)
    Image.fromarray(img).save(OUT / f"{item}.jpg", quality=90)
    return {"id": r.id, "status": "ok", "item": item, "yaw": yaw, "brightness": round(bright),
            "md5": hashlib.md5((OUT / f"{item}.jpg").read_bytes()).hexdigest()}


with cf.ThreadPoolExecutor(8) as ex:
    res = []
    for k, x in enumerate(ex.map(work, sel.itertuples()), 1):
        res.append(x)
        if k % 500 == 0:
            print(k, "/", len(sel), flush=True)
res = pd.DataFrame(res)
out = sel.merge(res, on="id")
dup = out.status.eq("ok") & out.duplicated("md5")
out.loc[dup, "status"] = "exact_duplicate"
for f in out.loc[dup, "item"]:
    (OUT / f"{f}.jpg").unlink(missing_ok=True)
ok = out[out.status == "ok"]
man = pd.DataFrame({
    "item": ok.item, "file": "main/" + ok.item + ".jpg", "parent_pano_id": ok.id, "side": "R", "yaw_off_from_travel": RIGHT_YAW_OFF,
    "street_id": ok.street_id, "split": ok.split, "position_group": ok.position_group, "lat": ok.lat, "lon": ok.lon,
    "captured_at": ok.captured, "creator": ok.creator, "sequence": ok.sequence, "travel_bearing": ok.travel_bearing.round(1),
    "yaw": ok.yaw, "brightness": ok.brightness, "dist_to_street_m": ok.dist_m.round(1), "source": "mapillary",
    "licence": "CC BY-SA 4.0", "mapillary_url": "https://www.mapillary.com/app/?pKey=" + ok.id, "phase": "main"})
man.to_csv(MAN / "main_v1.csv", index=False, encoding="utf-8-sig")
out[["id", "street_id", "split", "status", "brightness"]].to_csv(MAN / "main_v1_collection_status.csv", index=False)
summary = out.groupby(["split", "status"]).size().unstack(fill_value=0)
print(summary.to_string())
print(man.groupby(["split", "street_id"]).size().to_string())
with open(ROOT / "docs" / "collection_log.md", "a", encoding="utf-8") as f:
    f.write(f"\n## {date.today()} — Main collection v1 (`src/11_collect_main.py`, server)\n"
            f"- Streets/splits from configs/streets_v1.yaml; right crop yaw {RIGHT_YAW_OFF}; <= 2 panos per 25 m position (distinct days);"
            f" pilot positions skipped; cap {CAP} per street.\n"
            f"- Selected {len(sel)} panos; status counts: {out.status.value_counts().to_dict()}.\n"
            f"- Crops kept: {len(man)} -> by split {man.split.value_counts().to_dict()}.\n")
