"""SUPERSEDED 2026-11-11 by src/analysis/21_selector_benchmark.py, which compares occ_v1, occ_v2 and the embedding
selectors on all 1,839 main-phase train labels; this script was never run and is kept as a record only.
Exploratory: does occ_v2 (src/seg_measures.py) rank blocked crops better than occ_v1? Reference = the five pilot votes.
Rebuilds the 150 pilot_v2 crops from their panos (manifest yaw), segments them (masks cached), then on items with
>= 3 votes 0/1: AUC of each score for majority blocked (n1 > n0) with bootstrap 95% CI, and the blocked share in the
top third by score among crops with near_y >= 0.60. occ_v1 should reproduce 14_rule_check.py (AUC about 0.75).
Nothing here is a label. Needs MAPILLARY_TOKEN when the panos are not cached. A GPU is used when available.
Output: data/labels/pilot_report/pilot_scorer_check.csv"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import numpy as np
import pandas as pd
import py360convert
import requests
from PIL import Image

from common import CROP_FOV, CROP_PITCH, CROP_PX, DATA, env
from seg_measures import load_model, measures, segment

REP, PANO, OUT = DATA / "labels" / "pilot_report", DATA / "raw" / "pano", DATA / "crops" / "pilot_v2_rebuilt"
(OUT / "seg").mkdir(parents=True, exist_ok=True)
PANO.mkdir(parents=True, exist_ok=True)
man = pd.read_csv(DATA / "manifest" / "pilot_v2.csv", dtype={"parent_pano_id": str})
V = pd.read_csv(REP / "pilot_vote_counts.csv").rename(columns={"crop_id": "item", "0": "n0", "1": "n1", "I": "nI"})

S = None
for r in man.itertuples():
    cp = OUT / f"{r.item}.jpg"
    if cp.exists():
        continue
    p = PANO / f"{r.parent_pano_id}.jpg"
    if not p.exists():
        if S is None:
            S = requests.Session()
            S.headers["Authorization"] = f"OAuth {env('MAPILLARY_TOKEN')}"
        url = S.get(f"https://graph.mapillary.com/{r.parent_pano_id}", params={"fields": "thumb_2048_url"}, timeout=30).json()["thumb_2048_url"]
        p.write_bytes(requests.get(url, timeout=60).content)
    e = np.asarray(Image.open(p).convert("RGB"))
    img = py360convert.e2p(e, fov_deg=CROP_FOV, u_deg=r.yaw, v_deg=CROP_PITCH, out_hw=(CROP_PX, CROP_PX))
    Image.fromarray(img.astype(np.uint8)).save(cp, quality=90)

todo = [i for i in man.item if not (OUT / "seg" / f"{i}.npz").exists()]
if todo:
    model = load_model()
    for s in range(0, len(todo), 8):
        for i, seg in zip(todo[s:s + 8], segment(model, [OUT / f"{i}.jpg" for i in todo[s:s + 8]])):
            np.savez_compressed(OUT / "seg" / f"{i}.npz", seg=seg)
F = pd.DataFrame([{"item": i, **measures(np.load(OUT / "seg" / f"{i}.npz")["seg"])} for i in man.item]).merge(V, on="item")
F.round(3).to_csv(REP / "pilot_scorer_check.csv", index=False, encoding="utf-8-sig")


def auc(y, s):
    pos, neg = s[y], s[~y]
    return float((pos[:, None] > neg).mean() + 0.5 * (pos[:, None] == neg).mean()) if len(pos) and len(neg) else np.nan


old = pd.read_csv(REP / "pilot_rule_features.csv")
print("occ_v1 vs 14_rule_check occupancy, Spearman:",
      round(F.merge(old[["item", "occupancy"]], on="item")[["occ_v1", "occupancy"]].corr("spearman").iloc[0, 1], 3))
B = F[(F.n0 + F.n1) >= 3]
y = (B.n1 > B.n0).to_numpy()
idx = [np.random.RandomState(0).randint(0, len(y), len(y)) for _ in range(2000)]  # same resamples for every score
vis = F[F.near_y >= 0.60]
print(f"items {len(B)} | majority blocked {int(y.sum())} | random crop blocked {((F.n0 + F.n1 >= 3) & (F.n1 > F.n0)).mean():.0%}")
boot = {}
for col in ["occ_v1", "occ_v2", "n_v2"]:
    s = B[col].to_numpy()
    boot[col] = np.array([auc(y[b], s[b]) for b in idx])
    top = vis[vis[col].rank(pct=True, method="first") > 2 / 3]
    blk = ((top.n0 + top.n1 >= 3) & (top.n1 > top.n0)).mean()
    print(f"{col:7s} AUC {auc(y, s):.2f} [{np.nanpercentile(boot[col], 2.5):.2f}-{np.nanpercentile(boot[col], 97.5):.2f}]"
          f" | top third (near_y >= 0.60, n={len(top)}): blocked {blk:.0%} of crops")
d = boot["occ_v2"] - boot["occ_v1"]
lo, hi = np.nanpercentile(d, [2.5, 97.5])
verdict = "v2 better" if lo > 0 else "v2 worse" if hi < 0 else "no detectable difference"
print(f"AUC v2 - v1 (paired bootstrap): {np.nanmean(d):+.3f} [{lo:+.3f} to {hi:+.3f}] -> {verdict}")
print("decision rule fixed before running: use v2 unless it is worse; otherwise keep v1")
