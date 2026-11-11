"""Does picking crops by selector score also give a better classifier, or only more blocked crops? Simulation inside
the TRAIN split with the final human labels; val and test are not read. Nothing here is a label.
One round: the 10 train streets are split at random into base (4, already labelled), pool (3, "new streets": labels
hidden) and eval (3, unseen). A selector fitted on base scores the pool; a strategy picks BUDGET of the pool crops, whose
human labels are then revealed (as if people labelled them). A blocked-vs-clear classifier (logistic regression on the
same frozen embeddings, usable crops only) is trained on base + picked and scored on the eval streets.
Strategies
  none         base only
  random       uniform over the pool
  top          highest P(blocked)            (greedy positive search)
  mix70        70% top + 30% random          (rule of docs/data_enrichment.md)
  uncertain    P(blocked) closest to 0.5     (uncertainty sampling, Lewis & Gale 1994)
  all          the whole pool labelled       (upper reference, costs 1/BUDGET times more labels)
The downstream model is a linear probe, a proxy for the fine-tuned model of the project, so read the direction of the
differences, not their size.
Output: data/streets/enrichment_simulation.csv
Usage: python src/analysis/22_enrichment_simulation.py [--enc dinov2_b14] [--rounds 300]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, enrich.py

import argparse

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, f1_score

from common import DATA
from enrich import cached_embed, fit_selector

ap = argparse.ArgumentParser()
ap.add_argument("--enc", default="dinov2_b14")
ap.add_argument("--rounds", type=int, default=300)
ap.add_argument("--budget", type=float, default=0.20)
A = ap.parse_args()
C_SEL, C_CLF = 0.01, 0.01  # fixed: the inner CV of fit_selector would cost 300 x 6 x 12 fits

L = pd.read_csv(DATA / "labels" / "main_labels_v1.csv", dtype=str, keep_default_na=False)
L = L[L.split == "train"].reset_index(drop=True)
X = cached_embed(A.enc, L.item.tolist(), [DATA / "crops" / f for f in L.file])
lab, g = L.label.to_numpy(), L.street_id.to_numpy()
blocked, usable, streets, nat = lab == "1", lab != "I", np.unique(L.street_id), (L.phase == "main").to_numpy()
rng = np.random.RandomState(20261111)
STRATS = ["none", "random", "top", "mix70", "uncertain", "all"]
rows = []
for r in range(A.rounds):
    perm = rng.permutation(streets)
    base, pool, ev = np.isin(g, perm[:4]), np.where(np.isin(g, perm[4:7]) & nat)[0], np.isin(g, perm[7:]) & usable & nat
    if blocked[ev].sum() < 5:
        continue
    p = fit_selector(X[base], blocked[base], C=C_SEL)[0].predict_proba(X[pool])[:, 1]
    n = int(round(A.budget * len(pool)))
    n_top, order = int(0.7 * n), np.argsort(-p)
    rest = rng.permutation(order[n_top:])
    pick = {"none": pool[:0], "random": rng.choice(pool, n, replace=False), "top": pool[order[:n]],
            "mix70": pool[np.concatenate([order[:n_top], rest[: n - n_top]])],
            "uncertain": pool[np.argsort(np.abs(p - 0.5))[:n]], "all": pool}
    for s in STRATS:
        tr = np.concatenate([np.where(base & usable)[0], pick[s][usable[pick[s]]]])
        q = fit_selector(X[tr], blocked[tr], C=C_CLF)[0].predict_proba(X[ev])[:, 1]
        rows.append({"round": r, "strategy": s, "picked": len(pick[s]), "picked_blocked": int(blocked[pick[s]].sum()),
                     "picked_unusable": int((~usable[pick[s]]).sum()), "train_blocked": int(blocked[tr].sum()),
                     "AP": average_precision_score(blocked[ev], q), "F1": f1_score(blocked[ev], q >= 0.5)})
    if r % 50 == 0:
        print("round", r, flush=True)
R = pd.DataFrame(rows)
R.round(4).to_csv(DATA / "streets" / "enrichment_simulation.csv", index=False, encoding="utf-8-sig")
W = R.pivot(index="round", columns="strategy")
T = R.groupby("strategy")[["picked", "picked_blocked", "picked_unusable", "train_blocked", "AP", "F1"]].mean().loc[STRATS]
for m in ("AP", "F1"):
    d = W[m].sub(W[m]["random"], axis=0)
    T[f"d_{m}_vs_random"] = [f"{d[s].mean():+.3f} ± {1.96 * d[s].std() / np.sqrt(len(d)):.3f}" for s in STRATS]
    T[f"{m}_wins_vs_random"] = [(d[s] > 0).mean() for s in STRATS]
pd.set_option("display.width", 250, "display.max_columns", 30)
print(f"encoder {A.enc} | rounds {W.shape[0]} | budget {A.budget:.0%} of the pool")
print(T.round(3).to_string())
print("± = 1.96 standard errors over rounds; rounds reuse the same 10 streets, so the intervals are too narrow.")
