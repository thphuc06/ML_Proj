"""Train enrichment labelling done: label counts and selector check for the MAIN2_<name> projects
(created by 25_ls_create_train_extra.py; crops chosen by src/collection/23_collect_train_extra.py).
Reads a raw export folder (default: the newest data/labels/raw/train_extra_export_*; --fresh pulls a new read-only
export first). Each crop has one annotator, so there is no agreement figure here.
- labels per stratum. The top_score stratum is every pool crop with score >= the cut (the per-street cap never bound),
  and the random stratum is a uniform sample of the rest of the pool. So the blocked share of the whole pool, the
  selector's yield against random labelling of the same number of crops, and its recall over the pool can be estimated.
- blocked share by score band, road type, street; per street a pool-weighted blocked share against the street scan score
  of 24_street_scan.py (few crops per street: rough)
- per annotator: counts, seconds, difficult flag; reasons for I; obstacles for 1
Outputs: data/labels/train_extra_report/ (train_extra_labels.csv, report.md)
         data/labels/train_extra_labels_v1.csv (one row per crop, same columns as main_labels_v1.csv + stratum, score)
Usage: python src/labeling/26_train_extra_report.py [--fresh]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import json
from datetime import datetime

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from common import DATA

MAP = {"0 – Còn lối đi": "0", "1 – Bị chặn": "1", "Không đủ thông tin": "I"}
RAW, REP = DATA / "labels" / "raw", DATA / "labels" / "train_extra_report"
REP.mkdir(parents=True, exist_ok=True)
rng = np.random.RandomState(20261112)

if "--fresh" in sys.argv:
    from ls_client import BASE, projects, session
    src = RAW / f"train_extra_export_{datetime.now():%Y%m%d_%H%M}"
    src.mkdir(parents=True, exist_ok=True)
    s = session()
    for title, p in projects(s).items():
        if title.startswith("MAIN2_"):
            r = s.get(BASE + f"/api/projects/{p['id']}/export", params={"exportType": "JSON"}, timeout=300)
            r.raise_for_status()
            (src / f"{title}.json").write_text(json.dumps(r.json(), ensure_ascii=False), encoding="utf-8")
else:
    src = sorted(RAW.glob("train_extra_export_*"))[-1]

rows, dup = [], 0
for f in sorted(src.glob("MAIN2_*.json")):
    for t in json.loads(f.read_text(encoding="utf-8")):
        anns = sorted([a for a in t.get("annotations", []) if not a.get("was_cancelled")], key=lambda a: a["updated_at"])
        dup += max(0, len(anns) - 1)
        if not anns:
            continue
        a = anns[-1]
        res = {r["from_name"]: r["value"] for r in a["result"]}
        ch = lambda k: res.get(k, {}).get("choices", [])  # noqa: E731
        rows.append({"item": t["data"]["item"], "annotator": f.stem[6:], "label": MAP.get((ch("label") or [None])[0]),
                     "reason": "|".join(ch("reason")), "obstacles": "|".join(ch("obstacles")), "difficult": bool(ch("difficult")),
                     "note": " ".join(res.get("note", {}).get("text", [])), "seconds": a.get("lead_time"), "updated_at": a["updated_at"]})
lab = pd.DataFrame(rows)
asg = pd.read_csv(DATA / "manifest" / "train_extra_v1_assignment.csv", dtype=str)
man = pd.read_csv(DATA / "manifest" / "train_extra_v1.csv", dtype={"item": str})
pool = pd.read_csv(DATA / "streets" / "train_extra_v1_scores.csv", dtype={"item": str})
pool = pool[pool.status == "ok"]
scan = pd.read_csv(DATA / "streets" / "street_scan_v1.csv").set_index("street_id")
L = asg[["item", "annotator"]].merge(lab, on=["item", "annotator"], how="left").merge(
    man[["item", "street_id", "position_group", "stratum", "score"]], on="item")
L["highway"] = L.street_id.map(scan.highway)
missing, unknown = int(L.label.isna().sum()), int((L.label.isna() & L.updated_at.notna()).sum())
L.drop(columns=["note"]).to_csv(REP / "train_extra_labels.csv", index=False, encoding="utf-8-sig")
D = L[L.label.notna()].copy()
D["y"], D["usable"] = D.label == "1", D.label != "I"


def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


def share(d, name):
    k, n, u = int(d.y.sum()), len(d), int(d.usable.sum())
    lo, hi = wilson(k, n)
    return {"group": name, "crops": n, "0": int((d.label == "0").sum()), "1": k, "I": int((d.label == "I").sum()),
            "blocked/crop": round(k / n, 3) if n else np.nan, "95% CI": f"[{lo:.3f}, {hi:.3f}]",
            "blocked/usable": round(k / u, 3) if u else np.nan, "I share": round(1 - u / n, 3) if n else np.nan}


lines = []
P = lambda s="": lines.append(s)  # noqa: E731
P("# Train enrichment labels: report")
P()
P(f"Export: `{src.relative_to(DATA.parent).as_posix()}` (gitignored). Projects `MAIN2_*`, one annotator per crop.")
P(f"Labelled: {len(D)}/{len(L)} assigned crops; missing {missing}; unknown label value {unknown}; tasks saved more than once {dup} (latest kept).")
P()

# ---- 1. strata and the selector
P("## 1. Strata")
P()
T = pd.DataFrame([share(D, "all"), *[share(D[D.stratum == s], s) for s in ("top_score", "random")]])
P(T.to_markdown(index=False))
P()
N_POOL, N_TOP = len(pool), int((man.stratum == "top_score").sum())
cut = man[man.stratum == "top_score"].score.min()
n_rest = int((pool.score < cut).sum())
top, rnd = D[D.stratum == "top_score"], D[D.stratum == "random"]
b_top, r_rnd = top.y.sum(), rnd.y.mean()
assert int((pool.score >= cut).sum()) == N_TOP, "the top stratum is not a census of the pool above the cut"
B = []
for _ in range(2000):  # bootstrap within strata
    t = top.y.values[rng.randint(0, len(top), len(top))].mean() * N_TOP
    r = rnd.y.values[rng.randint(0, len(rnd), len(rnd))].mean()
    B.append((t, r * n_rest, (t + r * n_rest) / N_POOL))
B = np.array(B)
est_pool = (b_top + r_rnd * n_rest) / N_POOL
gain = D.y.mean() / est_pool
ci = lambda v: f"[{np.percentile(v, 2.5):.3f}, {np.percentile(v, 97.5):.3f}]"  # noqa: E731
P(f"- Pool: {N_POOL} crops. Top stratum = all {N_TOP} crops with score >= {cut:.3f}; random stratum = {len(rnd)} of the other {n_rest}.")
P(f"- Estimated blocked share of the whole pool (what random labelling would find): **{est_pool:.3f}** {ci(B[:, 2])}.")
P(f"- Blocked share of the 2,000 labelled crops: **{D.y.mean():.3f}**, i.e. **{gain:.1f}x** random labelling of the same pool "
  f"({D.y.sum()} blocked against about {est_pool * len(D):.0f}).")
P(f"- Top stratum vs random stratum: {top.y.mean():.3f} vs {r_rnd:.3f}.")
P(f"- Recall of the top stratum over the pool's blocked crops: {b_top / (b_top + r_rnd * n_rest):.2f} "
  f"{ci(B[:, 0] / (B[:, 0] + B[:, 1]))} (the top {N_TOP / N_POOL:.0%} of the pool).")
P("- On the 10 old train streets (benchmark, leave-one-street-out): 70/30 rule at 36-40% of the pool gave about 0.13 blocked per crop; "
  "random 0.058.")
P()

# ---- 2. score bands
P("## 2. Blocked share by score band")
P()
D["band"] = pd.cut(D.score, [0, 0.2, 0.4, 0.61, 0.7, 0.8, 0.9, 1.0], include_lowest=True)
P(pd.DataFrame([share(g, str(b)) for b, g in D.groupby("band", observed=True)]).to_markdown(index=False))
P()
P("Bands below 0.61 hold only random-stratum crops; bands above hold only top-stratum crops.")
P()

# ---- 3. road type and streets
P("## 3. Road type")
P()
P(pd.DataFrame([share(g, h) for h, g in D.groupby("highway")]).to_markdown(index=False))
P()
P("Within the random stratum only (no selection by score):")
P()
P(pd.DataFrame([share(g, h) for h, g in rnd.assign(highway=rnd.street_id.map(scan.highway), usable=rnd.label != "I").groupby("highway")]).to_markdown(index=False))
P()
pool["top"] = pool.score >= cut
S = []
for sid, g in D.groupby("street_id"):
    pt, pr = pool[(pool.street_id == sid) & pool.top], pool[(pool.street_id == sid) & ~pool.top]
    gt, gr = g[g.stratum == "top_score"], g[g.stratum == "random"]
    if len(gr) < 3:
        continue
    est = (gt.y.sum() + gr.y.mean() * len(pr)) / (len(pt) + len(pr))
    S.append({"street_id": sid, "highway": scan.highway.get(sid), "scan_score": scan.mean_score.get(sid), "labelled": len(g),
              "blocked": int(g.y.sum()), "random_crops": len(gr), "est_pool_blocked": round(est, 3)})
S = pd.DataFrame(S).sort_values("est_pool_blocked", ascending=False)
rho = spearmanr(S.scan_score, S.est_pool_blocked)
P("## 4. Streets")
P()
P(f"Pool-weighted blocked share per street (top-stratum count + random-stratum rate x the street's other crops), streets with >= 3 "
  f"random crops: {len(S)}. Spearman with the street scan score: **{rho.statistic:.2f}** (p = {rho.pvalue:.3f}). Few random crops per "
  "street, so each value is rough.")
P()
P(S.head(15).to_markdown(index=False))
P()
P("Lowest:")
P()
P(S.tail(8).to_markdown(index=False))
P()

# ---- 5. annotators and fields
P("## 5. Annotators")
P()
A = D.groupby("annotator").agg(crops=("label", "size"), zero=("label", lambda x: (x == "0").sum()), one=("label", lambda x: (x == "1").sum()),
                               insufficient=("label", lambda x: (x == "I").sum()), median_s=("seconds", "median"),
                               difficult=("difficult", "mean"))
A["blocked/crop"] = (A.one / A.crops).round(3)
A["blocked/crop random stratum"] = rnd.groupby("annotator").y.mean().round(3)
A["difficult"] = A.difficult.round(3)
A["median_s"] = A.median_s.round(1)
P(A.to_markdown())
P()
P("Crops were assigned at random, so large differences between annotators point at different reading of the guide, not at "
  "different images.")
P()
P("## 6. Reasons and obstacles")
P()
P("Reasons given for Không đủ thông tin: " + ", ".join(f"{k} {v}" for k, v in D[D.label == "I"].reason.replace("", "(none)").value_counts().items()))
P()
ob = D[D.label == "1"].obstacles.str.split("|").explode()
P("Obstacles on blocked crops: " + ", ".join(f"{k} {v}" for k, v in ob.replace("", "(none)").value_counts().items()))
P()
P(f"Obstacles tagged on crops labelled 0: {int((D[D.label == '0'].obstacles != '').sum())} of {int((D.label == '0').sum())}.")
P()
P(f"Notes: {int((L.note.fillna('') != '').sum())}.")
(REP / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

# ---- final table, same columns as main_labels_v1.csv
if missing == 0 and unknown == 0:
    fin = pd.DataFrame({"item": D["item"], "phase": "train_extra", "file": "train_extra_v1/" + D["item"] + ".jpg", "split": "train",
                        "street_id": D.street_id, "label": D.label, "source": "single", "reason": D.reason.where(D.label == "I", ""),
                        "stratum": D.stratum, "score": D.score})
    fin.to_csv(DATA / "labels" / "train_extra_labels_v1.csv", index=False, encoding="utf-8-sig")
print("\n".join(lines))
