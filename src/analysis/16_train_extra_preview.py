"""Exploratory: train enrichment preview (runs locally; nothing goes to Label Studio and no score here is a label).
Extra right crops from OTHER capture days at the train positions of main_v1, ranked by parked-vehicle occupancy so that
labelling effort finds more blocked sidewalks. Val and test are never touched.
Decision 2026-11-04 (docs/data_enrichment.md): this pool is not used. Enrichment waits for the first labelling round and
will draw from NEW train streets; this script stays as the record of the preview and as the base for that script.
1. Mapillary pano metadata only for the 0.001-deg cells within ~40 m of a train main_v1 pano (cached parquet).
2. Travel bearing as in 03 (images 2 before / 2 after in the sequence). A pano is a candidate for a main position when
   it is <= 15 m from a main pano of that position, travels the SAME way (<= 30 deg, so it sees the same sidewalk),
   was captured on a day that position does not use yet, by a creator and in a year already present in main_v1, and is
   not in main_v1 or the pilots. One pano per (position, day). New positions beyond the per-street cap need the OSM
   matching of 03 and are not covered here.
3. Download -> night filter -> right_crop, plus the paired main crop rebuilt from its manifest yaw. 64-bit dHash of
   both crops: near duplicate when Hamming <= DUP_BITS. Panos, crops and SegFormer masks are cached, so a run resumes.
4. src/seg_measures.py (SegFormer-B5 Cityscapes; GPU when available) -> near_y, occ_v1, occ_v2.
5. Ranking = --score (occ_v2 by default) among crops with near_y >= VIS.
   --sample: sheet of the v2 top, the v1 top that v2 dropped, and random crops, each beside the main crop of its position.
   --all:    selection of N_LABEL crops = TOP_SHARE by rank (at most STREET_CAP of them per street) + the rest at random
             among all usable crops; written to data/manifest/train_extra_v1.csv with the stratum of each crop.
Usage: python src/analysis/16_train_extra_preview.py --dry | --sample 80 | --all
Outputs: data/crops/train_extra/, data/streets/train_extra_preview_scores.csv, data/crops/train_extra_sheet.jpg
         (--all also data/manifest/train_extra_v1.csv)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import argparse
import concurrent.futures as cf
import os
import secrets
import threading
import time
from collections import defaultdict

import numpy as np
import pandas as pd
import py360convert
import requests
from PIL import Image, ImageDraw, ImageFont

from common import BBOX, CROP_FOV, CROP_PITCH, CROP_PX, DARK, DATA, RAW_META, bearing_xy, env, right_crop, to_xy

ap = argparse.ArgumentParser()
mode = ap.add_mutually_exclusive_group(required=True)
mode.add_argument("--dry", action="store_true", help="metadata and pool counts only")
mode.add_argument("--sample", type=int, help="random candidates spread over streets (small preview)")
mode.add_argument("--all", action="store_true", help="whole candidate pool, writes the selection")
ap.add_argument("--score", choices=["occ_v1", "occ_v2"], default="occ_v2", help="ranking score (17_check_scorer_pilot.py decides)")
A = ap.parse_args()

STEP, PAD, POS_M, AXIS_DEG, DUP_BITS, VIS = 0.001, 0.0004, 15, 30, 10, 0.60
N_LABEL, TOP_SHARE, STREET_CAP = 400, 0.7, 0.25
FIELDS = "id,captured_at,compass_angle,computed_compass_angle,computed_geometry,sequence,creator"
MAN, PANO, OUT = DATA / "manifest", DATA / "raw" / "pano", DATA / "crops" / "train_extra"
for d in (PANO, OUT / "main", OUT / "seg"):
    d.mkdir(parents=True, exist_ok=True)
rng = np.random.RandomState(20261104)
try:
    TOKEN = env("MAPILLARY_TOKEN")
except (FileNotFoundError, KeyError):
    raise SystemExit("MAPILLARY_TOKEN missing: copy .env.example to .env and fill it in")
S = requests.Session()
S.headers["Authorization"] = f"OAuth {TOKEN}"

main = pd.read_csv(MAN / "main_v1.csv", dtype={"parent_pano_id": str})
used = set(main.parent_pano_id)
for f in ("pilot_v1.csv", "pilot_v2.csv"):
    used |= set(pd.read_csv(MAN / f, dtype={"parent_pano_id": str}).parent_pano_id)
tm = main[main.split == "train"].reset_index(drop=True)
tm["day"] = tm.captured_at.str[:10]  # stamps are local time (+07:00)
tm["x"], tm["y"] = to_xy(tm.lon.values, tm.lat.values)
creators, years = set(main.creator), set(main.captured_at.str[:4])


# ---- 1. metadata for the cells around train positions
def query(x0, y0, x1, y1, depth=0):
    """Same cell query as 02_fetch_mapillary_meta.py: a cell hitting the 2000-row limit is split in 4."""
    for attempt in range(5):
        try:
            d = S.get("https://graph.mapillary.com/images", timeout=90, params={
                "bbox": f"{x0:.6f},{y0:.6f},{x1:.6f},{y1:.6f}", "fields": FIELDS, "limit": 2000, "is_pano": "true"}).json()
        except Exception:  # noqa: BLE001
            time.sleep(3 * (attempt + 1))
            continue
        msg = d.get("error", {}).get("message", "")
        rows = d.get("data", [])
        if ("reduce" in msg or len(rows) >= 2000) and depth < 3:
            xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
            return [r for b in [(x0, y0, xm, ym), (xm, y0, x1, ym), (x0, ym, xm, y1), (xm, ym, x1, y1)]
                    for r in query(*b, depth=depth + 1)]
        if msg:
            time.sleep(3 * (attempt + 1))
            continue
        return rows
    return [{"_failed_cell": [x0, y0, x1, y1]}]


s0, w0 = BBOX[0], BBOX[1]
cells = set()
for la, lo in zip(tm.lat, tm.lon):
    for dy in (-PAD, PAD):  # PAD < STEP, so the 4 corners of the box touch every cell it covers
        for dx in (-PAD, PAD):
            cells.add((int((lo + dx - w0) // STEP), int((la + dy - s0) // STEP)))
cache = RAW_META / "train_extra_cells.parquet"
if cache.exists():
    meta = pd.read_parquet(cache)
else:
    rows, failed, t0 = [], 0, time.time()
    with cf.ThreadPoolExecutor(8) as ex:
        boxes = [(w0 + i * STEP, s0 + j * STEP, w0 + (i + 1) * STEP, s0 + (j + 1) * STEP) for i, j in sorted(cells)]
        for res in ex.map(lambda b: query(*b), boxes):
            for r in res:
                if "_failed_cell" in r:
                    failed += 1
                    continue
                lon, lat = ((r.pop("computed_geometry", None) or {}).get("coordinates") or [None, None])[:2]
                rows.append({**r, "lon": lon, "lat": lat, "creator": (r.pop("creator", None) or {}).get("username")})
    meta = pd.DataFrame(rows).drop_duplicates("id")
    meta["captured"] = pd.to_datetime(meta.captured_at, unit="ms", utc=True).dt.tz_convert("Asia/Ho_Chi_Minh")
    meta.to_parquet(cache, index=False)
    print(f"cells {len(cells)} | failed {failed} | panos {len(meta)} | {time.time() - t0:.0f}s")

# ---- 2. travel bearing and candidates per main position
m = meta.dropna(subset=["lon", "lat"]).astype({"id": str}).sort_values(["sequence", "captured_at"]).reset_index(drop=True)
m["x"], m["y"] = to_xy(m.lon.values, m.lat.values)
tb = np.full(len(m), np.nan)
for idx in m.groupby("sequence").indices.values():
    xs, ys = m.x.values[idx], m.y.values[idx]
    for p, i in enumerate(idx):
        a, b = max(0, p - 2), min(len(idx) - 1, p + 2)
        if a != b and np.hypot(xs[b] - xs[a], ys[b] - ys[a]) > 3:
            tb[i] = bearing_xy(xs[a], ys[a], xs[b], ys[b])
m["travel_bearing"] = tb
m["day"] = m.captured.dt.strftime("%Y-%m-%d")
c = m[~m.id.isin(used) & m.creator.isin(creators) & m.captured.dt.year.astype(str).isin(years)
      & np.isfinite(m.travel_bearing)].reset_index(drop=True)
near, dist = np.empty(len(c), int), np.empty(len(c))
for k in range(0, len(c), 4000):
    d = np.hypot(c.x.values[k:k + 4000, None] - tm.x.values, c.y.values[k:k + 4000, None] - tm.y.values)
    near[k:k + 4000], dist[k:k + 4000] = d.argmin(1), d.min(1)
same_way = np.abs((c.travel_bearing.values - tm.travel_bearing.values[near] + 180) % 360 - 180) <= AXIS_DEG
c = c.assign(main_k=near, dist_main=dist, position_group=tm.position_group.values[near], street_id=tm.street_id.values[near])
c = c[(c.dist_main <= POS_M) & same_way]
used_days = tm.groupby("position_group").day.agg(set)
c = c[[d not in used_days[g] for d, g in zip(c.day, c.position_group)]]
c = c.sort_values("dist_main").drop_duplicates(["position_group", "day"]).reset_index(drop=True)
pool = c.groupby("street_id").agg(extra_panos=("id", "size"), positions_with_extra=("position_group", "nunique"))
pool["main_positions"] = tm.groupby("street_id").position_group.nunique()
print("candidate pool (other capture days at main positions, same direction):")
print(pool.to_string())
print("total", len(c))
if A.dry:
    raise SystemExit

# ---- 3. download, crop, near-duplicate check (all cached)
pick = c if A.all else pd.concat([g.sample(min(len(g), A.sample // len(pool)), random_state=rng) for _, g in c.groupby("street_id")])
locks = defaultdict(threading.Lock)  # several candidates share one main pano: never read a half-written file


def fetch(pid):
    p = PANO / f"{pid}.jpg"
    with locks[pid]:
        for _ in range(3):
            if p.exists():
                break
            try:
                url = S.get(f"https://graph.mapillary.com/{pid}", params={"fields": "thumb_2048_url"}, timeout=30).json()["thumb_2048_url"]
                tmp = p.with_suffix(".part")
                tmp.write_bytes(requests.get(url, timeout=60).content)
                os.replace(tmp, p)
            except Exception:  # noqa: BLE001
                pass
    return np.asarray(Image.open(p).convert("RGB")) if p.exists() else None


def dhash(img):
    g = np.asarray(Image.fromarray(img).convert("L").resize((9, 8), Image.LANCZOS), dtype=int)
    return (g[:, 1:] > g[:, :-1]).flatten()


def work(r):
    mr = tm.iloc[r.main_k]
    cp, mp = OUT / f"{r.id}.jpg", OUT / "main" / f"{mr['item']}.jpg"
    out = {"id": r.id, "main_item": mr["item"], "main_day": mr.day}
    e = fetch(r.id)
    if e is None:
        return {**out, "status": "download_failed"}
    bright = float(e[: e.shape[0] // 2].mean())
    if bright < DARK:
        return {**out, "status": "night", "brightness": round(bright)}
    if not cp.exists():
        ca = r.computed_compass_angle if r.computed_compass_angle == r.computed_compass_angle else r.compass_angle
        Image.fromarray(right_crop(e, r.travel_bearing, ca)[0]).save(cp, quality=90)
    if not mp.exists() and (em := fetch(mr.parent_pano_id)) is not None:
        mimg = py360convert.e2p(em, fov_deg=CROP_FOV, u_deg=mr.yaw, v_deg=CROP_PITCH, out_hw=(CROP_PX, CROP_PX))
        Image.fromarray(mimg.astype(np.uint8)).save(mp, quality=90)
    ham = int((dhash(np.asarray(Image.open(cp))) != dhash(np.asarray(Image.open(mp)))).sum()) if mp.exists() else None
    return {**out, "status": "near_duplicate" if ham is not None and ham <= DUP_BITS else "ok",
            "brightness": round(bright), "dhash_bits": ham}


t0 = time.time()
with cf.ThreadPoolExecutor(8) as ex:
    res = pd.DataFrame(list(ex.map(work, pick.itertuples())))
pick = pick.merge(res, on="id")
print(f"download / filter: {pick.status.value_counts().to_dict()} | {time.time() - t0:.0f}s")

# ---- 4. SegFormer masks (cached) and measures
from seg_measures import load_model, measures, segment  # noqa: E402

ok = pick[pick.status == "ok"].reset_index(drop=True)
todo = [i for i in ok.id if not (OUT / "seg" / f"{i}.npz").exists()]
if todo:
    model, t0 = load_model(), time.time()
    for s in range(0, len(todo), 8):
        for i, seg in zip(todo[s:s + 8], segment(model, [OUT / f"{i}.jpg" for i in todo[s:s + 8]])):
            np.savez_compressed(OUT / "seg" / f"{i}.npz", seg=seg)
        if (s // 8) % 25 == 0:
            print(f"segformer {s + len(todo[s:s + 8])}/{len(todo)} on {model[2]} | {time.time() - t0:.0f}s", flush=True)
    print(f"SegFormer: {len(todo)} crops in {time.time() - t0:.0f}s on {model[2]}")
ok = pd.concat([ok, pd.DataFrame([measures(np.load(OUT / "seg" / f"{i}.npz")["seg"]) for i in ok.id])], axis=1)
vis = ok.near_y >= VIS
ok["rank_v2"] = ok.occ_v2.where(vis).rank(ascending=False, method="first")
ok["rank_v1"] = ok.occ_v1.where(vis).rank(ascending=False, method="first")
print(f"near_y >= {VIS}: {vis.mean():.0%} of {len(ok)} crops | occ_v1 > 0: {(ok.occ_v1 > 0).mean():.0%},"
      f" occ_v2 > 0: {(ok.occ_v2 > 0).mean():.0%}")

# ---- 5a. --all: selection for labelling (not uploaded anywhere)
ok["stratum"] = ""
if A.all:
    n_top, per_street, top = int(N_LABEL * TOP_SHARE), int(N_LABEL * TOP_SHARE * STREET_CAP), []
    for k in ok[vis].sort_values("rank_v2" if A.score == "occ_v2" else "rank_v1").index:
        if len(top) < n_top and (ok.loc[top, "street_id"] == ok.street_id[k]).sum() < per_street:
            top.append(k)
    ok.loc[top, "stratum"] = f"top_{A.score}"
    rest = ok[ok.stratum == ""]
    ok.loc[rest.sample(min(N_LABEL - len(top), len(rest)), random_state=rng).index, "stratum"] = "random"
    sel = ok[ok.stratum != ""].assign(
        item=lambda d: [secrets.token_hex(4) for _ in range(len(d))], side="R", split="train", phase="train_extra",
        source="mapillary", licence="CC BY-SA 4.0", mapillary_url=lambda d: "https://www.mapillary.com/app/?pKey=" + d.id)
    sel.rename(columns={"id": "parent_pano_id"})[
        ["item", "parent_pano_id", "side", "street_id", "split", "position_group", "lat", "lon", "captured", "creator",
         "sequence", "travel_bearing", "stratum", "near_y", "occ_v1", "occ_v2", "main_item", "source", "licence", "mapillary_url", "phase"]
    ].round(4).to_csv(MAN / "train_extra_v1.csv", index=False, encoding="utf-8-sig")
    print("selection ->", MAN / "train_extra_v1.csv", sel.stratum.value_counts().to_dict())
    print(sel.groupby(["street_id", "stratum"]).size().unstack(fill_value=0).to_string())

pick.drop(columns=["main_k"]).merge(ok[["id", "near_y", "occ_v1", "occ_v2", "n_v2", "rank_v1", "rank_v2", "stratum"]], on="id", how="left")[
    ["id", "street_id", "position_group", "day", "main_item", "main_day", "dist_main", "status", "brightness", "dhash_bits",
     "near_y", "occ_v1", "occ_v2", "n_v2", "rank_v1", "rank_v2", "stratum", "creator"]
].round(3).to_csv(DATA / "streets" / "train_extra_preview_scores.csv", index=False, encoding="utf-8-sig")

# ---- 5b. sheet: v2 top, v1 top dropped by v2, random
K, DROP, RAND = 10, 4, 6
top2 = ok[ok.rank_v2 <= K].sort_values("rank_v2")
gone = ok[(ok.rank_v1 <= K) & ~ok.index.isin(top2.index)].sort_values("rank_v1").head(DROP)
rand = ok.drop(top2.index.union(gone.index)).sample(min(RAND, len(ok) - len(top2) - len(gone)), random_state=rng)
show = [(r, "TOP v2") for r in top2.itertuples()] + [(r, "v1 cũ, v2 loại") for r in gone.itertuples()] + \
       [(r, "NGẪU NHIÊN") for r in rand.itertuples()]
T, CAP_H, COLS = 320, 44, 4
sheet = Image.new("RGB", (COLS * (2 * T + 16), -(-len(show) // COLS) * (T + CAP_H)), "white")
dr = ImageDraw.Draw(sheet)
font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf" if os.name == "nt" else "DejaVuSans.ttf", 15)
for k, (r, tag) in enumerate(show):
    x0, y0 = (k % COLS) * (2 * T + 16), (k // COLS) * (T + CAP_H)
    ext = Image.open(OUT / f"{r.id}.jpg").resize((T, T))
    ImageDraw.Draw(ext).line([(0, int(0.6 * T)), (T, int(0.6 * T))], fill=(0, 160, 255), width=2)
    sheet.paste(ext, (x0, y0))
    if (OUT / "main" / f"{r.main_item}.jpg").exists():
        sheet.paste(Image.open(OUT / "main" / f"{r.main_item}.jpg").resize((T, T)), (x0 + T, y0))
    dr.text((x0 + 4, y0 + T + 2), f"#{k + 1} {tag} | {r.street_id} | v1 {r.occ_v1:.2f} v2 {r.occ_v2:.2f}", fill="black", font=font)
    dr.text((x0 + 4, y0 + T + 22), f"trái: thêm {r.day}   phải: main {r.main_day}", fill=(90, 90, 90), font=font)
sheet.save(DATA / "crops" / "train_extra_sheet.jpg", quality=88)
print("sheet ->", DATA / "crops" / "train_extra_sheet.jpg")
