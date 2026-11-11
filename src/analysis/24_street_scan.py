"""Which streets should train enrichment draw from? Scan of every well-covered street with the enrichment selector
(src/enrich.py; chosen by 21_selector_benchmark.py). A street-level score is a hint for picking streets, never a label.
Val and test labels are not read.
1. Streets: data/streets/street_candidates_v1.csv with >= MIN_POS positions. Dropped: streets of configs/streets_v1.yaml
   and every street sharing its name with a val/test street. Other components of a TRAIN street name are kept and
   flagged (same_name_as_train).
2. Per street: panos of the creators and years of main_v1, N_PER random 25 m grid cells, one random pano per cell
   (uniform over places, not over panos). Cells within 40 m of a val/test pano are skipped (coordinates only).
3. Download -> night filter -> right crop -> P(blocked) of the selector fitted on all train labels.
4. Per street: mean score with a bootstrap 95% interval, share of crops at or above the score that cuts the top 20% of
   the train crops, and est_blocked = the mean score mapped to a blocked share by a line fitted on the 10 train streets
   (their leave-one-street-out mean score against their labelled blocked share). Ten points: a rough guide only.
   Check printed first: Spearman correlation of that mean score with the blocked share over the 10 train streets.
Streets ranked on a noisy mean of N_PER crops: the top of the list is optimistic (winner's curse).
Usage: python src/analysis/24_street_scan.py [--n 30] [--min-pos 30] [--enc dinov2_b14]
Outputs: data/streets/street_scan_v1.csv, data/streets/street_scan_v1_crops.csv, docs/figures/street_scan_v1_sheet.jpg"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, enrich.py

import argparse
import concurrent.futures as cf
import os
import re
import time

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from scipy.stats import spearmanr

from common import DARK, DATA, RAW_META, ROOT, right_crop, to_xy
from enrich import ENCODERS, cached_embed, fetch_pano, fit_selector

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=30, help="crops per street")
ap.add_argument("--min-pos", type=int, default=30, help="minimum 25 m positions of a street (street_candidates_v1.csv)")
ap.add_argument("--enc", choices=list(ENCODERS), default="dinov2_b14")
A = ap.parse_args()
CELL_M, NEAR_EVAL_M, MIN_OK = 25, 40, 15
OUT = DATA / "crops" / "street_scan"
OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.RandomState(20261112)
log = lambda s: print(s, flush=True)  # noqa: E731


def base(street_id):
    return street_id.split("#")[0].strip().casefold()


# ---- 0. does a street's mean score follow its blocked share? (train streets, leave-one-street-out scores of script 21)
B = pd.read_csv(DATA / "streets" / "selector_benchmark_scores.csv")
B = B[B.phase == "main"].assign(y=lambda d: d.label.astype(str) == "1")
col = f"lr_{A.enc}"
cut = B[col].quantile(0.8)
T = B.groupby("street_id").agg(crops=("y", "size"), blocked=("y", "mean"), mean_score=(col, "mean"))
rho = spearmanr(T.blocked, T.mean_score)
slope, icpt = np.polyfit(T.mean_score, T.blocked, 1)
log(f"train streets: Spearman(mean {col}, blocked share) = {rho.statistic:.2f} (p = {rho.pvalue:.4f}, 10 streets)")
log(f"blocked share ~ {icpt:+.3f} {slope:+.3f} * mean score | score cutting the top 20% of train crops: {cut:.3f}")
log(T.round(3).sort_values("blocked", ascending=False).to_string())

# ---- 1. streets
V1 = {m.group(1): m.group(2) for m in re.finditer(r'id:\s*"([^"]+)",\s*split:\s*(\w+)', (ROOT / "configs" / "streets_v1.yaml").read_text(encoding="utf-8"))}
held, trn = {base(s) for s, sp in V1.items() if sp != "train"}, {base(s) for s, sp in V1.items() if sp == "train"}
C = pd.read_csv(DATA / "streets" / "street_candidates_v1.csv")
C = C[(C.positions_25m >= A.min_pos) & ~C.street_id.isin(V1) & ~C.street_id.map(base).isin(held)].set_index("street_id")
log(f"streets scanned: {len(C)} (>= {A.min_pos} positions, not in streets_v1.yaml, no val/test street name)")

# ---- 2. cells and panos
main = pd.read_csv(DATA / "manifest" / "main_v1.csv", dtype={"parent_pano_id": str})
match = pd.read_parquet(DATA / "streets" / "pano_street_match_v1.parquet").astype({"id": str})
meta = pd.read_parquet(sorted(RAW_META.glob("mapillary_pano_*.parquet"))[-1],
                       columns=["id", "compass_angle", "computed_compass_angle", "captured", "creator"]).astype({"id": str})
m = match[match.street_id.isin(C.index)].merge(meta, on="id")
m = m[m.creator.isin(set(main.creator)) & m.captured.dt.year.astype(str).isin(set(main.captured_at.str[:4]))]
m["x"], m["y"] = to_xy(m.lon.values, m.lat.values)
ex_, ey_ = to_xy(main.lon[main.split != "train"].values, main.lat[main.split != "train"].values)
near_eval = np.array([np.hypot(ex_ - x, ey_ - y).min() < NEAR_EVAL_M for x, y in zip(m.x.values, m.y.values)])
m = m[~near_eval]
m["cell"] = (m.x // CELL_M).astype(int).astype(str) + "_" + (m.y // CELL_M).astype(int).astype(str)
one = m.sample(frac=1, random_state=rng).drop_duplicates(["street_id", "cell"])  # one random pano per cell
sel = pd.concat([g.head(A.n) for _, g in one.groupby("street_id")]).reset_index(drop=True)  # rows are shuffled: head = random cells
log(f"panos to score: {len(sel)} on {sel.street_id.nunique()} streets")


# ---- 3. download, night filter, crop
def work(r):
    p = OUT / f"{r.id}.jpg"
    if p.exists():
        return {"id": r.id, "status": "ok"}
    e = fetch_pano(r.id)
    if e is None:
        return {"id": r.id, "status": "download_failed"}
    if float(e[: e.shape[0] // 2].mean()) < DARK:
        return {"id": r.id, "status": "night"}
    ca = r.computed_compass_angle if r.computed_compass_angle == r.computed_compass_angle else r.compass_angle
    Image.fromarray(right_crop(e, r.travel_bearing, ca)[0]).save(p, quality=90)
    return {"id": r.id, "status": "ok"}


t0, res = time.time(), []
with cf.ThreadPoolExecutor(8) as ex:
    for k, x in enumerate(ex.map(work, sel.itertuples()), 1):
        res.append(x)
        if k % 500 == 0:
            log(f"download/crop {k}/{len(sel)} | {time.time() - t0:.0f}s")
sel = sel.merge(pd.DataFrame(res), on="id")
log(f"download / filter: {sel.status.value_counts().to_dict()} | {time.time() - t0:.0f}s")
ok = sel[sel.status == "ok"].reset_index(drop=True)

# ---- 4. scores
L = pd.read_csv(DATA / "labels" / "main_labels_v1.csv", dtype=str, keep_default_na=False)
L = L[L.split == "train"].reset_index(drop=True)
clf, c = fit_selector(cached_embed(A.enc, L.item.tolist(), [DATA / "crops" / f for f in L.file], log=log),
                      (L.label == "1").to_numpy(), L.street_id.to_numpy())
ok["score"] = clf.predict_proba(cached_embed(A.enc, ok.id.tolist(), [OUT / f"{i}.jpg" for i in ok.id], log=log, cache="_street_scan"))[:, 1]
log(f"selector lr_{A.enc}_C{c:g} | crops scored: {len(ok)}")
ok[["id", "street_id", "cell", "lat", "lon", "creator", "score"]].round(5).to_csv(DATA / "streets" / "street_scan_v1_crops.csv", index=False, encoding="utf-8-sig")

rows = []
for sid, g in ok.groupby("street_id"):
    s = g.score.values
    bs = rng.choice(s, (2000, len(s))).mean(1)
    rows.append({"street_id": sid, "crops": len(s), "mean_score": s.mean(), "lo": np.percentile(bs, 2.5), "hi": np.percentile(bs, 97.5),
                 "share_top20_train": (s >= cut).mean(), "est_blocked": max(0.0, icpt + slope * s.mean())})
R = pd.DataFrame(rows).set_index("street_id")
R = R[R.crops >= MIN_OK].join(C[["positions_25m", "est_usable_crops", "highway", "centerline_km", "years", "markets", "lat", "lon"]])
R["same_name_as_train"] = R.index.map(base).isin(trn)
R = R.sort_values("mean_score", ascending=False)
R.round(3).to_csv(DATA / "streets" / "street_scan_v1.csv", encoding="utf-8-sig")
pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 40)
log(f"streets ranked: {len(R)} | mean score over all scanned crops: {ok.score.mean():.3f}")
log(R.drop(columns=["lat", "lon", "years"]).head(40).round(3).to_string())

# ---- sheet: the 12 highest streets, 6 random crops each
TOP, PER, T_, CAP_H = 12, 6, 240, 26
sheet = Image.new("RGB", (PER * (T_ + 4), TOP * (T_ + CAP_H)), "white")
dr = ImageDraw.Draw(sheet)
font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf" if os.name == "nt" else "DejaVuSans.ttf", 15)
for i, sid in enumerate(R.index[:TOP]):
    g = ok[ok.street_id == sid].sample(min(PER, (ok.street_id == sid).sum()), random_state=rng)
    dr.text((4, i * (T_ + CAP_H) + 2), f"#{i + 1} {sid} | điểm TB {R.mean_score[sid]:.2f} [{R.lo[sid]:.2f}; {R.hi[sid]:.2f}] | {int(R.crops[sid])} ảnh | 6 ảnh bốc ngẫu nhiên",
            fill="black", font=font)
    for j, r in enumerate(g.itertuples()):
        sheet.paste(Image.open(OUT / f"{r.id}.jpg").resize((T_, T_)), (j * (T_ + 4), i * (T_ + CAP_H) + CAP_H))
sheet.save(ROOT / "docs" / "figures" / "street_scan_v1_sheet.jpg", quality=85)
log(f"sheet -> {ROOT / 'docs' / 'figures' / 'street_scan_v1_sheet.jpg'}")
