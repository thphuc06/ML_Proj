"""Exploratory: where and how the five annotators diverge in the pilot (input for the guide v1 meeting).
A. each annotator against the leave-one-out majority of the other four (confusion and bias direction)
B. Dawid-Skene EM on the 3-way label: per-annotator confusion matrix without assuming any one person is right
C. reason agreement on items labelled insufficient, and obstacle tags versus the blocked vote
Output: printed tables, data/labels/pilot_report/pilot_annotator_bias.csv. Nothing here changes a label."""
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import numpy as np
import pandas as pd

from common import DATA

REP = DATA / "labels" / "pilot_report"
L = pd.read_csv(sorted(glob.glob(str(REP / "pilot_labels_*.csv")))[-1], dtype={"label": str}, keep_default_na=False)
W = L.pivot_table(index="crop_id", columns="annotator", values="label", aggfunc="first")
A, C = list(W.columns), ["0", "1", "I"]
pd.set_option("display.width", 200)

# ---- A. leave-one-out majority
rows = []
for a in A:
    others = W.drop(columns=a)
    cnt = pd.DataFrame({c: (others == c).sum(axis=1) for c in C})
    top = cnt.max(axis=1)
    maj = cnt.idxmax(axis=1).where((cnt == top.to_numpy()[:, None]).sum(axis=1) == 1)  # ties excluded
    s = pd.DataFrame({"me": W[a], "group": maj}).dropna()
    t = pd.crosstab(s.group, s.me).reindex(index=C, columns=C, fill_value=0)
    print(f"\n{a}: rows = majority of the other 4, cols = {a}, n={len(s)}\n{t.to_string()}")
    rows.append({"annotator": a, "n": len(s), "agree": round((s.me == s.group).mean(), 3),
                 "group0_says1": int(t.loc["0", "1"]), "group1_says0": int(t.loc["1", "0"]),
                 "group0_saysI": int(t.loc["0", "I"]), "groupI_says0": int(t.loc["I", "0"]),
                 "group1_saysI": int(t.loc["1", "I"]), "groupI_says1": int(t.loc["I", "1"])})
bias = pd.DataFrame(rows).set_index("annotator")
print("\n== disagreement direction versus the other four\n" + bias.to_string())
bias.to_csv(REP / "pilot_annotator_bias.csv", encoding="utf-8-sig")

# ---- B. Dawid-Skene
X = W[A].replace({c: i for i, c in enumerate(C)}).to_numpy(dtype=int)
n_i, n_a, n_c = X.shape[0], X.shape[1], 3
T = np.stack([(X == k).mean(axis=1) for k in range(n_c)], axis=1)
for _ in range(200):
    prior = T.mean(axis=0)
    Pi = np.full((n_a, n_c, n_c), 0.01)
    for a_ in range(n_a):
        for k in range(n_c):
            for l in range(n_c):
                Pi[a_, k, l] += T[X[:, a_] == l, k].sum()
    Pi /= Pi.sum(axis=2, keepdims=True)
    logT = np.log(prior) + sum(np.log(Pi[a_][:, X[:, a_]].T) for a_ in range(n_a))
    New = np.exp(logT - logT.max(axis=1, keepdims=True))
    New /= New.sum(axis=1, keepdims=True)
    if np.abs(New - T).max() < 1e-6:
        T = New
        break
    T = New
print("\n== Dawid-Skene estimated class shares (0, 1, I):", T.mean(axis=0).round(3))
for a_, a in enumerate(A):
    print(f"{a}: P(says 1 | truth 1)={Pi[a_, 1, 1]:.2f}  P(says 0 | truth 1)={Pi[a_, 1, 0]:.2f}  "
          f"P(says 1 | truth 0)={Pi[a_, 0, 1]:.2f}  P(says I | truth 0)={Pi[a_, 0, 2]:.2f}  P(says 0 | truth I)={Pi[a_, 2, 0]:.2f}")
ds = pd.DataFrame(T, index=W.index, columns=["p0", "p1", "pI"]).round(3)
ds.to_csv(REP / "pilot_dawid_skene.csv", encoding="utf-8-sig")

# ---- C. reasons and obstacles
I = L[L.label == "I"]
pair = I.groupby("crop_id").reason.agg(lambda s: s.value_counts(normalize=True).iloc[0] if len(s) >= 2 else np.nan).dropna()
print(f"\n== reason agreement on items with >= 2 'I' votes: mean top-reason share {pair.mean():.2f} on {len(pair)} items")
print(pd.crosstab(I.annotator, I.reason.replace("", "(missing)")).to_string())
mot = L.assign(moto=L.obstacles.str.contains("Xe máy"), obs=L.obstacles.str.len() > 0)
print("\n== share of images tagged with any obstacle / motorbike, by annotator and label")
print(mot.groupby(["annotator", "label"]).agg(n=("obs", "size"), any_obstacle=("obs", "mean"), motorbike=("moto", "mean")).round(2).to_string())
