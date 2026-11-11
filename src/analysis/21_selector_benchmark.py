"""Which scorer finds the most blocked crops per crop labelled? Reference = the final human labels of the TRAIN split
(data/labels/main_labels_v1.csv). Val and test are not read at all. Nothing here is a label.
Setting: enrichment labels crops from NEW streets, so every learned scorer is scored leave-one-street-out: the crops
of a street are ranked by a model that saw the other nine train streets only (pilot crops of those streets included).
Target: y = 1 for 'Bị chặn', 0 for 'Còn lối đi' AND 'Không đủ thông tin' -> precision = blocked crops per crop a person
would have to label. Metrics are computed on the 1,839 main-phase crops (natural distribution; the 150 pilot crops
were sampled with a model and are used for fitting only).
Scorers
  occ_v1, occ_v2   old pipeline (16_train_extra_preview.py): crops with near_y >= 0.60 ranked by occupancy, the rest last
  zs_<enc>         CLIP / SigLIP zero-shot: blocked prompts minus clear prompts (prompts fixed before the run)
  lr_<enc>         logistic regression on frozen embeddings (src/enrich.py), C by street-grouped inner CV
SegFormer-B5 needs about 7-11 s per crop on a laptop CPU, so the old scores are computed on a seeded random subset of
--seg-n main-phase crops (cached, resumable; -1 = all). Table 1 = every other scorer on all crops; table 2 = all scorers
on that subset, with paired bootstrap differences against occ_v2.
Outputs: data/streets/selector_benchmark.csv (metrics), data/streets/selector_benchmark_scores.csv (out-of-fold scores)
Usage: python src/analysis/21_selector_benchmark.py [--seg-n 800] [--enc clip_b16 dinov2_b14 ...]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, enrich.py

import argparse
import concurrent.futures as cf
import time

import numpy as np
import pandas as pd
from PIL import Image
from sklearn.metrics import average_precision_score, roc_auc_score

from common import DATA
from enrich import ENCODERS, cached_embed, crop_at_yaw, fetch_pano, fit_selector, text_embed

ap = argparse.ArgumentParser()
ap.add_argument("--seg-n", type=int, default=800, help="main-phase crops scored by the old pipeline (0 = none, -1 = all)")
ap.add_argument("--enc", nargs="*", default=list(ENCODERS))
A = ap.parse_args()
VIS, BUDGETS, NBOOT = 0.60, (0.10, 0.20, 1 / 3), 2000
POS = ["a street photo of a sidewalk blocked by parked motorbikes", "a street photo of a sidewalk blocked by street vendor stalls",
       "a street photo of a sidewalk completely occupied by parked vehicles and goods"]
NEG = ["a street photo of a clear empty sidewalk", "a street photo of a road with traffic", "a street photo of an intersection"]
CROPS, SEG = DATA / "crops", DATA / "crops" / "seg"
SEG.mkdir(parents=True, exist_ok=True)
log = lambda s: print(s, flush=True)  # noqa: E731

L = pd.read_csv(DATA / "labels" / "main_labels_v1.csv", dtype=str, keep_default_na=False)
L = L[L.split == "train"].reset_index(drop=True)
y, g, nat = (L.label == "1").to_numpy(), L.street_id.to_numpy(), (L.phase == "main").to_numpy()

# ---- crops: the server holds the originals; rebuild missing ones from the pano and the manifest yaw
man = pd.read_csv(DATA / "manifest" / "main_v1.csv", dtype={"parent_pano_id": str}).set_index("item")


def rebuild(r):
    p = CROPS / r.file
    if not p.exists() and (e := fetch_pano(man.parent_pano_id[r.item], keep=False)) is not None:
        Image.fromarray(crop_at_yaw(e, man.yaw[r.item])).save(p, quality=90)
    return p.exists()


with cf.ThreadPoolExecutor(8) as ex:
    have = np.array(list(ex.map(rebuild, L.itertuples())))
assert have.all(), f"{(~have).sum()} crops could not be rebuilt"
paths = [CROPS / f for f in L.file]
log(f"train crops {len(L)} | main {nat.sum()} (blocked {y[nat].sum()}) | pilot {(~nat).sum()} (blocked {y[~nat].sum()})")

# ---- scores
S, rng = {}, np.random.RandomState(20261111)
tie = rng.rand(len(L)) * 1e-9  # occupancy has many exact ties (0): break them at random, not by file order
order = rng.permutation(np.where(nat)[0])  # seeded order: a longer run extends the same subset


def loso(X):
    out, cs = np.zeros(len(L)), []
    for s in np.unique(g):
        tr = g != s
        clf, c = fit_selector(X[tr], y[tr], g[tr])
        out[~tr] = clf.predict_proba(X[~tr])[:, 1]
        cs.append(c)
    return out, cs


for enc in A.enc:
    X = cached_embed(enc, L.item.tolist(), paths, log=log)
    if ENCODERS[enc][1] == "clip":
        sim = X @ text_embed(enc, POS + NEG).T
        S[f"zs_{enc}"] = sim[:, :len(POS)].max(1) - sim[:, len(POS):].max(1)
    t0 = time.time()
    S[f"lr_{enc}"], cs = loso(X)
    log(f"lr_{enc}: C per fold {cs} | {time.time() - t0:.0f}s")


# ---- metrics
def metrics(s, yy):
    o = np.argsort(-s)
    m = {"AP": average_precision_score(yy, s), "AUC": roc_auc_score(yy, s)}
    for b in BUDGETS:
        m[f"hit@{b:.0%}"] = yy[o[: int(round(b * len(yy)))]].mean()
    return m


def policy(s, yy, gg, budget=0.20, top_share=0.7, cap=0.25):
    """Blocked crops per labelled crop for the selection rule of docs/data_enrichment.md section 5: top_share of the
    budget by score (at most cap of that part per street), the rest at random (expected value)."""
    n_lab = int(round(budget * len(yy)))
    n_top, per, top, cnt = int(n_lab * top_share), int(n_lab * top_share * cap), [], {}
    for k in np.argsort(-s):
        if len(top) < n_top and cnt.get(gg[k], 0) < per:
            top.append(k)
            cnt[gg[k]] = cnt.get(gg[k], 0) + 1
    rest = np.ones(len(yy), bool)
    rest[top] = False
    return (yy[top].sum() + (n_lab - len(top)) * yy[rest].mean()) / n_lab


def table(idx, ref=None):
    """Metrics of every scorer in S on the crops idx; bootstrap = crops resampled within each street, the same
    resamples for every scorer, so differences against ref are paired."""
    yn, gn = y[idx], g[idx]
    boots = [np.concatenate([rng.choice(np.where(gn == s)[0], (gn == s).sum()) for s in np.unique(gn)]) for _ in range(NBOOT)]
    rows, B = [], {}
    for name, s in S.items():
        sn = s[idx]
        m = metrics(sn, yn)
        m["policy@20%"] = policy(sn, yn, gn)
        m["streets_won@20%"] = sum(  # streets where the scorer's top 20% beats that street's own base rate
            yn[gn == st][np.argsort(-sn[gn == st])[: int(round(0.2 * (gn == st).sum()))]].mean() > yn[gn == st].mean() for st in np.unique(gn))
        B[name] = np.array([[(mm := metrics(sn[b], yn[b]))["AP"], mm["hit@20%"], mm["hit@33%"]] for b in boots])
        rows.append({"scorer": name, **m})
    R = pd.DataFrame(rows).set_index("scorer")
    for k, col in enumerate(["AP", "hit@20%", "hit@33%"]):
        R[f"{col}_ci"] = [f"[{np.percentile(B[s][:, k], 2.5):.3f}, {np.percentile(B[s][:, k], 97.5):.3f}]" for s in R.index]
        if ref:
            d = {s: B[s][:, k] - B[ref][:, k] for s in R.index}
            R[f"d_{col}_vs_{ref}"] = [f"{d[s].mean():+.3f} [{np.percentile(d[s], 2.5):+.3f}, {np.percentile(d[s], 97.5):+.3f}]" for s in R.index]
    log(f"crops {len(idx)} | blocked {yn.sum()} | random labelling finds {yn.mean():.1%} blocked per crop")
    log(R.round(3).to_string())
    return R.round(4).assign(n=len(idx), blocked=int(yn.sum()))


pd.set_option("display.width", 300, "display.max_columns", 40)
out = [table(np.where(nat)[0]).assign(table="all main-phase train crops")]

# ---- old pipeline on the seeded subset
n_seg = nat.sum() if A.seg_n < 0 else A.seg_n
if n_seg:
    from seg_measures import load_model, measures, segment
    sub = order[:n_seg]
    todo = [k for k in sub if not (SEG / f"{L.item[k]}.npz").exists()]
    if todo:
        model, t0 = load_model(), time.time()
        for s in range(0, len(todo), 4):
            ks = todo[s:s + 4]
            for k, seg in zip(ks, segment(model, [paths[k] for k in ks])):
                np.savez_compressed(SEG / f"{L.item[k]}.npz", seg=seg)
            if (s // 4) % 25 == 0:
                log(f"segformer {s + len(ks)}/{len(todo)} | {time.time() - t0:.0f}s")
    M = pd.DataFrame([measures(np.load(SEG / f"{L.item[k]}.npz")["seg"]) for k in sub], index=sub)
    for c in ("occ_v1", "occ_v2"):
        S[c] = np.full(len(L), np.nan)
        S[c][sub] = np.where(M.near_y >= VIS, M[c] + tie[sub], -1 + tie[sub])
    log(f"near_y >= {VIS}: {(M.near_y >= VIS).mean():.0%} of the subset | occ_v2 > 0: {(M.occ_v2 > 0).mean():.0%}")
    out.append(table(sub, ref="occ_v2").assign(table="seeded subset with SegFormer scores"))
pd.concat(out).to_csv(DATA / "streets" / "selector_benchmark.csv", encoding="utf-8-sig")
pd.DataFrame({"item": L.item, "phase": L.phase, "street_id": g, "label": L.label, **{k: np.round(v, 5) for k, v in S.items()}}).to_csv(
    DATA / "streets" / "selector_benchmark_scores.csv", index=False, encoding="utf-8-sig")
