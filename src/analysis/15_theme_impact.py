"""Exploratory: which disagreement themes cost the most agreement in the pilot?
Each of the 73 non-unanimous items was put in one theme by visual review (Claude, not a label). For each theme we
recompute Fleiss kappa as if the team fully agreed on that theme (all five votes set to the item's majority), which gives
an upper bound on the gain from settling that theme. Output: data/labels/pilot_report/pilot_review_items.csv."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import numpy as np
import pandas as pd

from common import DATA

THEMES = {
    "A_vi_he_xa": [37, 38, 42, 44, 48, 50, 51, 52, 53, 55, 57, 58, 59, 61, 62, 65, 68, 69],
    "B_giao_lo_khoang_trong": [18, 29, 39, 40, 43, 49, 56, 67, 70, 72],
    "C_bi_che_tien_canh": [30, 31, 32, 33, 36, 45, 46, 47],
    "D_chay_sang": [60, 63],
    "E_lan_mot_phan": [1, 2, 3, 6, 8, 9, 10, 11, 12, 14, 16, 17, 21, 23, 26, 27, 28, 41],
    "F_xe_nguoi_tam_thoi": [0, 4],
    "G_thong_thoang_bi_cham_khac": [5, 7, 19, 20, 22, 24, 25, 54, 64, 66, 71],
    "H_chan_ro": [13, 15, 34, 35],
}
REP = DATA / "labels" / "pilot_report"
x = pd.read_csv(REP / "pilot_nonunanimous.csv", encoding="utf-8-sig", index_col=0)
F = pd.read_csv(REP / "pilot_rule_features.csv", encoding="utf-8-sig", index_col=0)
assert sorted(i for v in THEMES.values() for i in v) == sorted(x.idx)
theme = {i: k for k, v in THEMES.items() for i in v}
x["theme"] = x.idx.map(theme)
x.join(F[["near_y", "occupancy"]]).sort_values("idx").to_csv(REP / "pilot_review_items.csv", encoding="utf-8-sig")

V = F[["n0", "n1", "nI"]].copy()


def fleiss(t):
    t = np.asarray(t, float)
    n = t.sum(axis=1)[0]
    p = t.sum(axis=0) / t.sum()
    P = ((t ** 2).sum(axis=1) - n) / (n * (n - 1))
    pe = (p ** 2).sum()
    return (P.mean() - pe) / (1 - pe)


def binary(t):
    keep = t[(t.nI == 0)]
    return fleiss(keep[["n0", "n1"]])


def resolved(ids):
    t = V.copy()
    for i in ids:
        r = t.loc[i, ["n0", "n1", "nI"]]
        k = r.idxmax()
        t.loc[i, ["n0", "n1", "nI"]] = 0
        t.loc[i, k] = 5
    return t


base = fleiss(V)
print("baseline Fleiss 3-way", round(base, 3))
rows = []
for k, v in THEMES.items():
    ids = x.index[x.idx.isin(v)]
    t = resolved(ids)
    miss = ((5 - x.loc[ids, ["0", "1", "I"]].max(axis=1))).sum()
    rows.append({"theme": k, "items": len(v), "off_majority_votes": int(miss), "kappa_if_settled": round(fleiss(t), 3),
                 "gain": round(fleiss(t) - base, 3)})
r = pd.DataFrame(rows).sort_values("gain", ascending=False)
print(r.to_string(index=False))
order, ids, out = r.theme.tolist(), [], []
for k in order:
    ids += list(x.index[x.idx.isin(THEMES[k])])
    out.append((k, round(fleiss(resolved(ids)), 3)))
print("cumulative:", out)
