"""Train enrichment: right crops from NEW train streets, picked for labelling by the embedding selector that replaced
the SegFormer occupancy ranking (docs/data_enrichment.md section 7; benchmark: src/analysis/21_selector_benchmark.py).
Nothing is uploaded to Label Studio and no score here is a label. Val and test labels are never read.
1. Streets: configs/streets_train_extra.yaml (status "proposed" until the team decides). Refused: a street that is
   already in configs/streets_v1.yaml, or that shares its name with a val/test street (other components included).
2. Panos: data/streets/pano_street_match_v1.parquet (run 01-03 first if missing), only creators and capture years of
   main_v1. Positions as in 11_collect_main.py: greedy thinning >= 25 m, up to 2 panos from distinct capture days per
   position, cap per street. Dropped: positions within NEAR_EVAL_M of a val/test pano (same place seen from a crossing
   street) and within 15 m of any pano already in a manifest.
3. Download -> night filter (brightness < DARK) -> common.right_crop -> exact duplicates (md5) and near duplicates
   (64-bit dHash, Hamming <= DUP_BITS, against the other capture day of the same position). Everything is cached.
4. Score = P(blocked) of the selector fitted on ALL train labels of data/labels/main_labels_v1.csv (blocked vs
   everything else a person labelled), frozen --enc embeddings, C by street-grouped CV (src/enrich.py).
5. --all: --n crops (default 2,000) = TOP_SHARE by score (at most STREET_CAP of that part per street) + the rest at random among
   the remaining crops -> data/manifest/train_extra_v1.csv (phase=train_extra, stratum, score, selector), a sample
   sheet for the team, and data/manifest/train_extra_v1_assignment.csv: every crop to one annotator of the main round,
   equal shares, at random (an annotator cannot tell the stratum of a crop). --sample N: N panos spread over the streets, sheet only. --dry: counts only, no download.
Usage: python src/collection/23_collect_train_extra.py --dry | --sample 120 | --all [--enc dinov2_b14]
Outputs: data/crops/train_extra_v1/, data/streets/train_extra_v1_scores.csv, data/crops/train_extra_v1_sheet.jpg
         (--all also data/manifest/train_extra_v1.csv and docs/figures/train_extra_v1_sheet.jpg)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, enrich.py

import argparse
import concurrent.futures as cf
import hashlib
import os
import re
import shutil
import time

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from common import DARK, DATA, RAW_META, RIGHT_YAW_OFF, ROOT, right_crop, to_xy
from enrich import ENCODERS, cached_embed, fetch_pano, fit_selector

ap = argparse.ArgumentParser()
mode = ap.add_mutually_exclusive_group(required=True)
mode.add_argument("--dry", action="store_true", help="pool counts only, no download")
mode.add_argument("--sample", type=int, help="this many panos spread over the streets; sheet only, no manifest")
mode.add_argument("--all", action="store_true", help="whole pool; writes the selection manifest")
ap.add_argument("--enc", choices=list(ENCODERS), default="dinov2_b14", help="encoder of the selector (winner of script 21)")
ap.add_argument("--n", type=int, default=2000, help="crops to select for labelling (--all)")
A = ap.parse_args()

THIN_M, PASS_M, NEAR_EVAL_M, DUP_BITS = 25, 15, 40, 10
N_LABEL, TOP_SHARE, STREET_CAP = A.n, 0.7, 0.25
MAN, OUT = DATA / "manifest", DATA / "crops" / "train_extra_v1"
OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.RandomState(20261111)
log = lambda s: print(s, flush=True)  # noqa: E731


def base(street_id):
    return street_id.split("#")[0].strip().casefold()


# ---- 1. streets and the val/test guard
def streets_of(path):
    return {m.group(1): m.group(2) for m in re.finditer(r'id:\s*"([^"]+)",\s*split:\s*(\w+)', path.read_text(encoding="utf-8"))}


CFG = ROOT / "configs" / "streets_train_extra.yaml"
cfg = CFG.read_text(encoding="utf-8")
STATUS, CAP = re.search(r"^status:\s*(\w+)", cfg, re.M).group(1), int(re.search(r"cap_r_crops_per_street:\s*(\d+)", cfg).group(1))
V1, NEW = streets_of(ROOT / "configs" / "streets_v1.yaml"), streets_of(CFG)
held = {base(s) for s, sp in V1.items() if sp != "train"}
bad = [s for s, sp in NEW.items() if sp != "train" or s in V1 or base(s) in held]
if bad or not NEW:
    raise SystemExit(f"refused: {bad} must be new train streets whose name is not a val/test street name (streets_v1.yaml)")
log(f"streets {len(NEW)} (status: {STATUS}) | selector encoder {A.enc}")
if STATUS != "approved":
    log("NOTE: the street list is a proposal, so every output of this run is a proposal as well.")

# ---- 2. positions
mfile = DATA / "streets" / "pano_street_match_v1.parquet"
if not mfile.exists():
    raise SystemExit(f"{mfile} missing: run src/collection/01_osm_streets.py, 02_fetch_mapillary_meta.py, 03_rank_streets.py first")
match = pd.read_parquet(mfile).astype({"id": str})
missing = sorted(set(NEW) - set(match.street_id))
if missing:
    raise SystemExit(f"no matched pano for {missing}: check the street ids against data/streets/street_candidates_v1.csv")
meta = pd.read_parquet(sorted(RAW_META.glob("mapillary_pano_*.parquet"))[-1],
                       columns=["id", "compass_angle", "computed_compass_angle", "captured", "creator"]).astype({"id": str})
main = pd.read_csv(MAN / "main_v1.csv", dtype={"parent_pano_id": str})
known = pd.concat([main] + [pd.read_csv(MAN / f, dtype={"parent_pano_id": str}) for f in ("pilot_v1.csv", "pilot_v2.csv") if (MAN / f).exists()])
m = match[match.street_id.isin(NEW)].merge(meta, on="id")
n0 = len(m)
m = m[m.creator.isin(set(main.creator)) & m.captured.dt.year.astype(str).isin(set(main.captured_at.str[:4])) & ~m.id.isin(set(known.parent_pano_id))]
m = m.assign(day=m.captured.dt.date)
m["x"], m["y"] = to_xy(m.lon.values, m.lat.values)
ex_, ey_ = to_xy(main.lon[main.split != "train"].values, main.lat[main.split != "train"].values)  # coordinates only, no labels
kx_, ky_ = to_xy(known.lon.values, known.lat.values)

sel, dropped = [], {"near_val_test": 0, "already_used": 0}
for sid, g in m.groupby("street_id"):
    g = g.sample(frac=1, random_state=rng).reset_index(drop=True)
    xy = g[["x", "y"]].values
    centres = []
    for k in range(len(g)):
        if all(np.hypot(*(xy[k] - xy[q])) >= THIN_M for q in centres):
            centres.append(k)
    pos = []
    for gi, k in enumerate(centres):
        if np.hypot(ex_ - xy[k][0], ey_ - xy[k][1]).min() < NEAR_EVAL_M:
            dropped["near_val_test"] += 1
            continue
        if np.hypot(kx_ - xy[k][0], ky_ - xy[k][1]).min() < PASS_M:
            dropped["already_used"] += 1
            continue
        near = g[np.hypot(*(xy - xy[k]).T) <= PASS_M].sort_values("sequence").drop_duplicates("day")  # one pano per capture day
        pos.append(near.sample(min(2, len(near)), random_state=rng).assign(position_group=f"{sid}|{gi}"))
    rng.shuffle(pos)
    taken, n = [], 0
    for p in pos:
        if n + len(p) > CAP:
            break
        taken.append(p)
        n += len(p)
    sel.append(pd.concat(taken))
sel = pd.concat(sel).drop_duplicates("id").reset_index(drop=True)
log(f"matched panos {n0} -> same creators/years, unused: {len(m)} | positions dropped: {dropped}")
log(sel.groupby("street_id").agg(panos=("id", "size"), positions=("position_group", "nunique")).to_string())
log(f"pool: {len(sel)} panos, {sel.position_group.nunique()} positions")
if A.dry:
    raise SystemExit
if A.sample:
    per = max(1, A.sample // sel.street_id.nunique())
    sel = pd.concat([g.sample(min(len(g), per), random_state=rng) for _, g in sel.groupby("street_id")]).reset_index(drop=True)
sel["item"] = [hashlib.sha1(f"train_extra|{i}".encode()).hexdigest()[:8] for i in sel.id]  # opaque and stable across runs
assert sel.item.is_unique and not set(sel.item) & set(known["item"])


# ---- 3. download, night filter, crop, duplicates (crops cached by item code)
def dhash(img):
    g = np.asarray(Image.fromarray(img).convert("L").resize((9, 8), Image.LANCZOS), dtype=int)
    return (g[:, 1:] > g[:, :-1]).flatten()


def work(r):
    p = OUT / f"{r.item}.jpg"
    e = fetch_pano(r.id)
    if e is None:
        return {"id": r.id, "status": "download_failed"}
    bright = float(e[: e.shape[0] // 2].mean())
    if bright < DARK:
        return {"id": r.id, "status": "night", "brightness": round(bright)}
    ca = r.computed_compass_angle if r.computed_compass_angle == r.computed_compass_angle else r.compass_angle
    img, yaw = right_crop(e, r.travel_bearing, ca)
    if not p.exists():
        Image.fromarray(img).save(p, quality=90)
    return {"id": r.id, "status": "ok", "yaw": yaw, "brightness": round(bright), "md5": hashlib.md5(p.read_bytes()).hexdigest(),
            "dhash": dhash(np.asarray(Image.open(p).convert("RGB")))}


t0, res = time.time(), []
with cf.ThreadPoolExecutor(8) as ex:
    for k, x in enumerate(ex.map(work, sel.itertuples()), 1):
        res.append(x)
        if k % 200 == 0:
            log(f"download/crop {k}/{len(sel)} | {time.time() - t0:.0f}s")
out = sel.merge(pd.DataFrame(res), on="id")
okm = out.status.eq("ok")
out.loc[okm & out[okm].duplicated("md5").reindex(out.index, fill_value=False), "status"] = "exact_duplicate"
for _, gidx in out[out.status == "ok"].groupby("position_group").groups.items():
    for a, b in zip(gidx[:-1], gidx[1:]):  # at most 2 crops per position
        if (out.dhash[a] != out.dhash[b]).sum() <= DUP_BITS:
            out.loc[b, "status"] = "near_duplicate"
log(f"download / filter: {out.status.value_counts().to_dict()} | {time.time() - t0:.0f}s")
ok = out[out.status == "ok"].reset_index(drop=True)

# ---- 4. selector fitted on every train label; scores for the candidates
L = pd.read_csv(DATA / "labels" / "main_labels_v1.csv", dtype=str, keep_default_na=False)
L = L[L.split == "train"].reset_index(drop=True)  # val and test rows are dropped before anything is used
lost = [f for f in L.file if not (DATA / "crops" / f).exists()]
if lost:
    raise SystemExit(f"{len(lost)} train crops missing in data/crops: run src/analysis/21_selector_benchmark.py once (it rebuilds them)")
Xtr = cached_embed(A.enc, L.item.tolist(), [DATA / "crops" / f for f in L.file], log=log)
clf, C = fit_selector(Xtr, (L.label == "1").to_numpy(), L.street_id.to_numpy())
SELECTOR = f"lr_{A.enc}_C{C:g}"
t0 = time.time()
ok["score"] = clf.predict_proba(cached_embed(A.enc, ok.item.tolist(), [OUT / f"{i}.jpg" for i in ok.item], log=log, cache="_train_extra"))[:, 1]
log(f"selector {SELECTOR}: fitted on {len(L)} train crops ({(L.label == '1').sum()} blocked) | candidates scored: {len(ok)} | {time.time() - t0:.0f}s")
log(ok.groupby("street_id").score.describe()[["count", "mean", "50%", "max"]].round(3).to_string())

# ---- 5. selection: TOP_SHARE by score with a per-street cap, the rest at random
n_label = N_LABEL if A.all else min(N_LABEL, int(round(len(ok) * 0.35)))  # --sample: about the share of the pool that --all labels
n_top, per_street, top, cnt = int(n_label * TOP_SHARE), max(1, int(n_label * TOP_SHARE * STREET_CAP)), [], {}
for k in ok.sort_values("score", ascending=False).index:
    if len(top) < n_top and cnt.get(ok.street_id[k], 0) < per_street:
        top.append(k)
        cnt[ok.street_id[k]] = cnt.get(ok.street_id[k], 0) + 1
ok["stratum"] = ""
ok.loc[top, "stratum"] = "top_score"
rest = ok[ok.stratum == ""]
ok.loc[rest.sample(min(n_label - len(top), len(rest)), random_state=rng).index, "stratum"] = "random"
ok["rank"] = ok.score.rank(ascending=False, method="first").astype(int)
pick = ok[ok.stratum != ""]
log(f"selection {len(pick)} of {len(ok)} crops: {pick.stratum.value_counts().to_dict()}")
log(pick.groupby(["street_id", "stratum"]).size().unstack(fill_value=0).to_string())
out.merge(ok[["id", "score", "rank", "stratum"]], on="id", how="left")[
    ["id", "item", "street_id", "position_group", "day", "status", "brightness", "score", "rank", "stratum", "creator"]
].round(4).to_csv(DATA / "streets" / "train_extra_v1_scores.csv", index=False, encoding="utf-8-sig")
if A.all:
    pd.DataFrame({
        "item": pick.item, "file": "train_extra_v1/" + pick.item + ".jpg", "parent_pano_id": pick.id, "side": "R",
        "yaw_off_from_travel": RIGHT_YAW_OFF, "street_id": pick.street_id, "split": "train", "position_group": pick.position_group,
        "lat": pick.lat, "lon": pick.lon, "captured_at": pick.captured, "creator": pick.creator, "sequence": pick.sequence,
        "travel_bearing": pick.travel_bearing.round(1), "yaw": pick.yaw, "brightness": pick.brightness, "dist_to_street_m": pick.dist_m.round(1),
        "source": "mapillary", "licence": "CC BY-SA 4.0", "mapillary_url": "https://www.mapillary.com/app/?pKey=" + pick.id,
        "phase": "train_extra", "stratum": pick.stratum, "score": pick.score.round(4), "selector": SELECTOR, "streets_status": STATUS,
    }).sample(frac=1, random_state=rng).to_csv(MAN / "train_extra_v1.csv", index=False, encoding="utf-8-sig")  # shuffled: row order says nothing
    log(f"manifest -> {MAN / 'train_extra_v1.csv'}")
    who = sorted(pd.read_csv(MAN / "main_v1_assignment.csv").annotator.unique())
    asg = pick.sample(frac=1, random_state=rng)
    pd.DataFrame({"item": asg.item, "annotator": [who[k % len(who)] for k in range(len(asg))], "role": "train_extra_single",
                  "file": "train_extra_v1/" + asg.item + ".jpg", "split": "train", "street_id": asg.street_id}
                 ).to_csv(MAN / "train_extra_v1_assignment.csv", index=False, encoding="utf-8-sig")
    log(f"assignment -> {MAN / 'train_extra_v1_assignment.csv'}: {len(asg)} crops, {len(who)} annotators")

# ---- sheet for the team: highest scores, the lowest scores that still made the top stratum, random picks
K_TOP, K_EDGE, K_RAND = 12, 6, 6
tops = ok[ok.stratum == "top_score"].sort_values("score", ascending=False)
rand = ok[ok.stratum == "random"]
show = [(r, "ĐIỂM CAO NHẤT") for r in tops.head(K_TOP).itertuples()] + \
       [(r, "CUỐI TẦNG ĐIỂM") for r in tops.iloc[K_TOP:].tail(K_EDGE).itertuples()] + \
       [(r, "NGẪU NHIÊN") for r in rand.sample(min(K_RAND, len(rand)), random_state=rng).itertuples()]
T, CAP_H, COLS = 320, 44, 6
sheet = Image.new("RGB", (COLS * (T + 8), -(-len(show) // COLS) * (T + CAP_H)), "white")
dr = ImageDraw.Draw(sheet)
font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf" if os.name == "nt" else "DejaVuSans.ttf", 15)
for k, (r, tag) in enumerate(show):
    x0, y0 = (k % COLS) * (T + 8), (k // COLS) * (T + CAP_H)
    im = Image.open(OUT / f"{r.item}.jpg").resize((T, T))
    ImageDraw.Draw(im).line([(0, int(0.6 * T)), (T, int(0.6 * T))], fill=(0, 160, 255), width=2)  # the 3/5 line of guide v1
    sheet.paste(im, (x0, y0))
    dr.text((x0 + 4, y0 + T + 2), f"#{k + 1} {tag}", fill="black", font=font)
    dr.text((x0 + 4, y0 + T + 22), f"{r.street_id} | điểm {r.score:.2f} (hạng {r.rank}/{len(ok)})", fill=(90, 90, 90), font=font)
sheet.save(DATA / "crops" / "train_extra_v1_sheet.jpg", quality=88)
log(f"sheet -> {DATA / 'crops' / 'train_extra_v1_sheet.jpg'}")
if A.all:
    shutil.copy(DATA / "crops" / "train_extra_v1_sheet.jpg", ROOT / "docs" / "figures" / "train_extra_v1_sheet.jpg")
