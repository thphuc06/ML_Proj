"""Exploratory: test candidate labelling rules on the 150 pilot crops (input for the guide v1 meeting).
SegFormer-B5 (Cityscapes) measures each crop; the five annotators' votes are the reference. Nothing here is a label.
Eligibility (is the near sidewalk visible enough?): target = at least 3 of 5 votes are 0/1.
  sw_low   sidewalk share of the lower half of the image
  sw_total sidewalk share of the whole image
  near_y   how low the sidewalk reaches: lowest row (0 top, 1 bottom) where sidewalk covers >= 10% of the row
  width    widest row covered by sidewalk, as a share of image width
Blocked (is a continuous strip left?): on items with >= 3 votes 0/1, target = blocked vote share n1/(n0+n1).
  For each row in a zone: walkway = sidewalk + obstacles (motorbike, bicycle, car, truck, bus, person, rider) between the
  outermost sidewalk pixels; free_ratio = longest run of plain sidewalk / walkway span; zone score = 10th percentile
  over rows. moto_widths = longest free run / median parked-motorbike blob width in that crop.
  Zones: near (rows >= 0.60), mid (0.40-0.60), all (>= 0.40). Comparing near vs mid tests rule R1.
Outputs: data/labels/pilot_report/pilot_rule_features.csv, printed AUC / threshold tables with bootstrap 95% CI."""
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import numpy as np
import pandas as pd
import torch
from PIL import Image
from scipy import ndimage
from scipy.stats import spearmanr
from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

from common import DATA

REP = DATA / "labels" / "pilot_report"
L = pd.read_csv(sorted(glob.glob(str(REP / "pilot_labels_*.csv")))[-1], dtype={"label": str}, keep_default_na=False)
W = L.pivot_table(index="crop_id", columns="annotator", values="label", aggfunc="first")
V = pd.DataFrame({k: (W == c).sum(axis=1) for k, c in [("n0", "0"), ("n1", "1"), ("nI", "I")]})

ROAD, SW, PERSON, RIDER, CAR, TRUCK, BUS, MOTO, BIKE = 0, 1, 11, 12, 13, 14, 15, 17, 18
OBST = [PERSON, RIDER, CAR, TRUCK, BUS, MOTO, BIKE]
H = 512


def run(arr):
    """Longest run of True in a 1-D array."""
    best = cur = 0
    for v in arr:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best


def zone(m, lo, hi, moto_w):
    ratios, widths = [], []
    for y in range(int(lo * H), int(hi * H), 4):
        row = m[y]
        xs = np.where(row == SW)[0]
        if len(xs) < 0.05 * H:
            continue
        seg = row[xs[0]:xs[-1] + 1]
        free = run(seg == SW)
        ratios.append(free / len(seg))
        widths.append(free)
    if not ratios:
        return np.nan, np.nan
    return float(np.percentile(ratios, 10)), float(np.percentile(widths, 10) / moto_w) if moto_w else np.nan


def parked(m):
    """Stationary obstacles on the sidewalk, lower half: blobs touching sidewalk and containing no rider."""
    near_sw = ndimage.binary_dilation(m == SW, iterations=6)
    near_rider = ndimage.binary_dilation(m == RIDER, iterations=6)
    blobs, n = ndimage.label(np.isin(m, [CAR, TRUCK, BUS, MOTO, BIKE]))
    mask = np.zeros_like(m, dtype=bool)
    for k in range(1, n + 1):
        b = blobs == k
        if b.sum() > 150 and (b & near_sw).any() and not (b & near_rider).any():
            mask |= b
    low, sw = mask[H // 2:].sum(), (m[H // 2:] == SW).sum()
    return low / (H * H / 2), low / max(low + sw, 1)


proc = SegformerImageProcessor.from_pretrained("nvidia/segformer-b5-finetuned-cityscapes-1024-1024")
net = SegformerForSemanticSegmentation.from_pretrained("nvidia/segformer-b5-finetuned-cityscapes-1024-1024").cuda().eval().half()
ids, rows = list(V.index), []
with torch.no_grad():
    for s in range(0, len(ids), 8):
        batch = ids[s:s + 8]
        ims = [Image.open(DATA / "crops" / "pilot_v2" / f"{i}.jpg").convert("RGB").resize((H, H)) for i in batch]
        lg = net(pixel_values=proc(images=ims, return_tensors="pt").to("cuda")["pixel_values"].half()).logits
        seg = torch.nn.functional.interpolate(lg.float(), size=(H, H), mode="bilinear").argmax(1).cpu().numpy()
        for i, m in zip(batch, seg):
            sw = m == SW
            share = sw.mean(axis=1)
            low = np.where(share >= 0.10)[0]
            blobs, n = ndimage.label(m == MOTO)
            mw = [np.ptp(np.where(blobs == k)[1]) + 1 for k in range(1, n + 1) if (blobs == k).sum() > 300]
            moto_w = float(np.median(mw)) if mw else None
            r = {"item": i, "sw_low": sw[H // 2:].mean(), "sw_total": sw.mean(), "near_y": (low.max() / H if len(low) else 0.0),
                 "width": share.max(), "road_low": (m[H // 2:] == ROAD).mean(), "obst_low": np.isin(m[H // 2:], OBST).mean(), "n_moto": len(mw)}
            r["parked_low"], r["occupancy"] = parked(m)
            r["free_near"], r["moto_near"] = zone(m, 0.60, 1.00, moto_w)
            r["free_mid"], r["moto_mid"] = zone(m, 0.40, 0.60, moto_w)
            r["free_all"], r["moto_all"] = zone(m, 0.40, 1.00, moto_w)
            rows.append(r)
F = pd.DataFrame(rows).set_index("item").join(V)
F.round(3).to_csv(REP / "pilot_rule_features.csv", encoding="utf-8-sig")


def auc(y, s):
    pos, neg = s[y], s[~y]
    if not len(pos) or not len(neg):
        return np.nan
    return float((pos[:, None] > neg).mean() + 0.5 * (pos[:, None] == neg).mean())


def ci(fn, n, B=2000, seed=0):
    r = np.random.RandomState(seed)
    v = [fn(r.randint(0, n, n)) for _ in range(B)]
    return np.nanpercentile(v, [2.5, 97.5])


def best_threshold(y, s):
    """Threshold maximising balanced accuracy of `s >= t` for target y."""
    ts = np.unique(np.round(s, 2))
    ba = [((s[y] >= t).mean() + (s[~y] < t).mean()) / 2 for t in ts]
    k = int(np.argmax(ba))
    return float(ts[k]), float(ba[k])


pd.set_option("display.width", 200)
print("== ELIGIBILITY: target = at least 3 of 5 votes are 0/1")
E = F.assign(y=(F.n0 + F.n1) >= 3)
clear = E[(E[["n0", "n1", "nI"]].max(axis=1) >= 4)]
for col in ["sw_low", "sw_total", "near_y", "width"]:
    y, s = E.y.to_numpy(), E[col].to_numpy()
    lo, hi = ci(lambda b: auc(y[b], s[b]), len(y))
    t, ba = best_threshold(y, s)
    yc, sc = clear.y.to_numpy(), clear[col].to_numpy()
    print(f"{col:9s} AUC {auc(y, s):.2f} [{lo:.2f}-{hi:.2f}] | clear-only AUC {auc(yc, sc):.2f} | best t={t:.2f} bal.acc={ba:.2f}"
          f" | agrees with majority on {(((s >= t) == y).mean()):.0%}")
for a, c in [(0.65, 0.05), (0.70, 0.05), (0.75, 0.05), (0.80, 0.05), (0.85, 0.05), (0.90, 0.05), (0.95, 0.05)]:
    pred = (E.near_y >= a) & (E.width >= 0.20)
    print(f"  rule near_y>={a:.2f} and width>=0.20: agrees {(pred == E.y).mean():.0%} | keeps {pred.mean():.0%} of images")

print("\n== BLOCKED: eligible items, target = blocked vote share; majority = n1 >= 3 or n1 > n0")
B = F[(F.n0 + F.n1) >= 3].assign(share=lambda d: d.n1 / (d.n0 + d.n1))
B = B.assign(y=B.n1 > B.n0)
print(f"items {len(B)} | majority blocked {int(B.y.sum())} | any blocked vote {int((B.n1 > 0).sum())}")
for col, sign in [("free_near", -1), ("free_mid", -1), ("free_all", -1), ("moto_near", -1), ("moto_mid", -1), ("moto_all", -1), ("obst_low", 1), ("parked_low", 1), ("occupancy", 1)]:
    d = B.dropna(subset=[col])
    rho = spearmanr(d[col], d.share).statistic
    y, s = d.y.to_numpy(), sign * d[col].to_numpy()
    lo, hi = ci(lambda b: auc(y[b], s[b]), len(y))
    t, ba = best_threshold(y, s)
    print(f"{col:10s} n={len(d):3d} spearman {rho:+.2f} | AUC {auc(y, s):.2f} [{lo:.2f}-{hi:.2f}] | best threshold {sign * t:.2f} bal.acc={ba:.2f}")
nb = B[B.n1 == 0]
print("\nfree_near percentiles: unanimous-clear items", nb.free_near.quantile([.1, .5, .9]).round(2).tolist(),
      "| items with 1-2 blocked votes", B[B.n1.between(1, 2)].free_near.quantile([.1, .5, .9]).round(2).tolist(),
      "| majority blocked", B[B.y].free_near.quantile([.1, .5, .9]).round(2).tolist())

print("\n== ELIGIBILITY threshold stability (near_y, bootstrap of the best threshold, and 5-fold out-of-sample agreement)")
y, s = E.y.to_numpy(), E.near_y.to_numpy()
r = np.random.RandomState(1)
th = [best_threshold(y[b], s[b])[0] for b in (r.randint(0, len(y), len(y)) for _ in range(1000))]
print("best threshold median", round(float(np.median(th)), 2), "95% range", np.percentile(th, [2.5, 97.5]).round(2))
fold = np.random.RandomState(2).permutation(len(y)) % 5
oos = [((s[fold == k] >= best_threshold(y[fold != k], s[fold != k])[0]) == y[fold == k]).mean() for k in range(5)]
print("5-fold agreement", round(float(np.mean(oos)), 3))
for t_ in (0.50, 0.55, 0.60, 0.65, 0.70, 0.75):
    print(f"  near_y >= {t_:.2f}: agrees {((s >= t_) == y).mean():.0%} | eligible {(s >= t_).mean():.0%} (group majority {y.mean():.0%})")

print("\n== per annotator: implicit thresholds")
W2 = W.reindex(F.index)
print(f"{'':6s}{'I: near_y of items called I vs not':38s}{'blocked: occupancy where called 1 vs 0':40s}")
for a_ in W2.columns:
    I_, N_ = F.near_y[W2[a_] == "I"], F.near_y[W2[a_] != "I"]
    e = F[W2[a_].isin(["0", "1"])]
    one, zero = e.occupancy[W2[a_][e.index] == "1"], e.occupancy[W2[a_][e.index] == "0"]
    yy = (W2[a_][e.index] == "1").to_numpy()
    print(f"{a_:6s}I med {I_.median():.2f} / rest {N_.median():.2f} | best split {best_threshold((W2[a_] != 'I').to_numpy(), F.near_y.to_numpy())[0]:.2f}"
          f"      | 1 med {one.median():.2f} / 0 med {zero.median():.2f} | AUC {auc(yy, e.occupancy.to_numpy()):.2f} | best split {best_threshold(yy, e.occupancy.to_numpy())[0]:.2f}")
