"""EDA for the tabular part of the data report: metadata and labels (no image pixels, no duplicate/leakage checks).
Descriptive only: val/test labels are used for descriptive statistics, never to select, tune or recommend anything.
Groups are always kept apart: "main tự nhiên" (phase main; train / val / test, natural distribution), pilot (150 crops, sampled
by a model-score stratum, not natural) and train_extra (top_score vs random; selected by a model score, biased).
Any pooled row is named as pooled in its label (main_all, extra_all, ...).

Inputs (read-only, utf-8-sig):
  data/labels/main_labels_v1.csv, data/labels/train_extra_labels_v2.csv
  data/manifest/main_v1.csv, pilot_v2.csv, train_extra_v1.csv, main_v1_collection_status.csv
  data/streets/train_extra_v1_scores.csv, street_candidates_v1.csv, street_scan_v1.csv
  data/labels/main_report/main_labels.csv, main_items.csv, data/labels/train_extra_report/train_extra_labels.csv
  configs/streets_v1.yaml, configs/streets_train_extra.yaml
Outputs:
  docs/data_report/tables/*.csv and tabular_numbers.json (every headline number)
  docs/data_report/figures/tab_*.pdf (vector). Optional: --png DIR also writes PNG previews to DIR (outside the repo).
Deterministic (seeded bootstrap), re-runnable, overwrites only its own outputs. Run from the repo root:
  .venv\\Scripts\\python.exe src/eda/28_eda_tabular.py [--png DIR]
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from scipy import stats
from scipy.spatial import cKDTree

from common import BBOX, DATA, ROOT, to_xy

OUT = ROOT / "docs" / "data_report"
TAB, FIG = OUT / "tables", OUT / "figures"
TAB.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
PNG = Path(sys.argv[sys.argv.index("--png") + 1]) if "--png" in sys.argv else None
if PNG:
    PNG.mkdir(parents=True, exist_ok=True)
SEED, B = 20261114, 1000  # bootstrap seed and number of street-cluster resamples

C0, C1, CI = "#4C78A8", "#E45756", "#9D9D9D"  # label 0 / 1 / I
LABCOL = {"0": C0, "1": C1, "I": CI}
LABNAME = {"0": "Còn lối đi (0)", "1": "Bị chặn (1)", "I": "Không đủ thông tin (I)"}
GORDER = ["main_train", "main_val", "main_test", "pilot", "extra_top_score", "extra_random"]
GNAME = {"main_train": "Main tự nhiên – train", "main_val": "Main tự nhiên – val", "main_test": "Main tự nhiên – test",
         "pilot": "Pilot (train)", "extra_top_score": "Train-extra – top_score", "extra_random": "Train-extra – random"}
GCOL = {"main_train": "#3B7D5B", "main_val": "#7FB89A", "main_test": "#B9DCC9", "pilot": "#F28E2B",
        "extra_top_score": "#7B4F9D", "extra_random": "#C3A3D9"}
CRE_COL = {"phoenix_mapping_front": "#E69F00", "bemaps3_sg": "#009E73", "phoenixmap_front": "#F0E442",
           "theonenetwork": "#CC79A7", "bemaps1": "#56B4E9", "bemaps2_hn": "#8C564B"}
ANN_VN = {"Hoc": "Học", "Khai": "Khải", "Loan": "Loan", "Minh": "Minh", "Phuc": "Phúc"}
TAGS = ["Xe máy đậu", "Hàng hóa / quầy hàng", "Bàn ghế quán", "Ô tô đậu", "Rào chắn / công trình", "Khác"]
REASONS = ["Không thấy vỉa hè", "Bị che", "Ảnh mờ / tối / cháy sáng", "Lý do khác"]

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
                     "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8, "pdf.fonttype": 42,
                     "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 100,
                     "axes.titleweight": "regular", "axes.titlelocation": "left"})

NUM = {}  # headline numbers -> tabular_numbers.json


def vn(n):
    return f"{int(n):,}".replace(",", ".")


def rd(path, **kw):
    head = pd.read_csv(path, encoding="utf-8-sig", nrows=0).columns
    dt = {c: str for c in ("item", "label", "label_v1", "label1", "label2", "label_prov", "label_final") if c in head}
    return pd.read_csv(path, encoding="utf-8-sig", dtype=dt, **kw)


def wcsv(df, name, index=False):
    df.to_csv(TAB / name, index=index, encoding="utf-8-sig")
    print(f"  table  {name}  ({len(df)} rows)")


def savefig(fig, name):
    fig.savefig(FIG / name, bbox_inches="tight")
    print(f"  figure {name}")
    if PNG:
        fig.savefig(PNG / (Path(name).stem + ".png"), bbox_inches="tight", dpi=130)
    plt.close(fig)


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (np.nan, np.nan, np.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, min(p, max(0.0, c - h)), max(p, min(1.0, c + h)))


def desc(x):
    x = pd.Series(x).dropna().astype(float)
    if len(x) == 0:
        return dict(n=0)
    q1, q3 = x.quantile(0.25), x.quantile(0.75)
    return dict(n=len(x), mean=x.mean(), median=x.median(), variance=x.var(ddof=1) if len(x) > 1 else np.nan,
                std=x.std(ddof=1) if len(x) > 1 else np.nan, min=x.min(), q1=q1, q3=q3, max=x.max(), iqr=q3 - q1)


# ------------------------------------------------------------------ load
print("loading")
P = lambda *a: DATA.joinpath(*a)
LAB = rd(P("labels", "main_labels_v1.csv"))
EXL = rd(P("labels", "train_extra_labels_v2.csv"))
MAN = {"main": rd(P("manifest", "main_v1.csv")), "pilot": rd(P("manifest", "pilot_v2.csv")),
       "extra": rd(P("manifest", "train_extra_v1.csv"))}
STAT = rd(P("manifest", "main_v1_collection_status.csv"))
POOL = rd(P("streets", "train_extra_v1_scores.csv"))
ANN_M = rd(P("labels", "main_report", "main_labels.csv"))
ITEMS_M = rd(P("labels", "main_report", "main_items.csv"))
ANN_X = rd(P("labels", "train_extra_report", "train_extra_labels.csv"))
CAND = rd(P("streets", "street_candidates_v1.csv"))
SCAN = rd(P("streets", "street_scan_v1.csv"))
YM = yaml.safe_load((ROOT / "configs" / "streets_v1.yaml").read_text(encoding="utf-8"))["streets"]
YX = yaml.safe_load((ROOT / "configs" / "streets_train_extra.yaml").read_text(encoding="utf-8"))["streets"]
TABLES = {  # name -> (relative path, dataframe)
    "main_labels_v1": ("data/labels/main_labels_v1.csv", LAB), "train_extra_labels_v2": ("data/labels/train_extra_labels_v2.csv", EXL),
    "main_v1 (manifest)": ("data/manifest/main_v1.csv", MAN["main"]), "pilot_v2 (manifest)": ("data/manifest/pilot_v2.csv", MAN["pilot"]),
    "train_extra_v1 (manifest)": ("data/manifest/train_extra_v1.csv", MAN["extra"]),
    "main_v1_collection_status": ("data/manifest/main_v1_collection_status.csv", STAT),
    "train_extra_v1_scores (candidate pool)": ("data/streets/train_extra_v1_scores.csv", POOL),
    "main_report/main_labels (annotations)": ("data/labels/main_report/main_labels.csv", ANN_M),
    "main_report/main_items": ("data/labels/main_report/main_items.csv", ITEMS_M),
    "train_extra_report/train_extra_labels (annotations)": ("data/labels/train_extra_report/train_extra_labels.csv", ANN_X),
    "street_candidates_v1": ("data/streets/street_candidates_v1.csv", CAND), "street_scan_v1": ("data/streets/street_scan_v1.csv", SCAN)}

# ------------------------------------------------------------------ master table D (one row per labelled crop)
drop = ["file", "split", "street_id", "phase", "source"]
mm = MAN["main"].rename(columns={c: c + "_man" for c in drop})
mp = MAN["pilot"].rename(columns={c: c + "_man" for c in drop}).rename(columns={"sampling_stratum": "pilot_stratum"})
mx = MAN["extra"].rename(columns={c: c + "_man" for c in drop} | {"stratum": "stratum_man", "score": "score_man"})
Lm, Lp = LAB[LAB.phase == "main"], LAB[LAB.phase == "pilot"]
D = pd.concat([Lm.merge(mm, on="item", how="left"), Lp.merge(mp, on="item", how="left"),
               EXL.merge(mx, on="item", how="left")], ignore_index=True)
D["group"] = np.where(D.phase == "main", "main_" + D.split, np.where(D.phase == "pilot", "pilot", "extra_" + D.stratum))
dt = pd.to_datetime(D.captured_at, format="ISO8601")
D["year"], D["month"], D["hour"] = dt.dt.year, dt.dt.month, dt.dt.hour
D["highway"] = D.street_id.map(CAND.drop_duplicates("street_id").set_index("street_id").highway)
D["bear_sin"], D["bear_cos"] = np.sin(np.radians(D.travel_bearing)), np.cos(np.radians(D.travel_bearing))
D["usable"] = D.label.isin(["0", "1"])
D["blocked"] = D.label == "1"
assert D.group.isin(GORDER).all() and len(D) == 5149
SUB = {"main_all": D[D.phase == "main"], "main_train": D[D.group == "main_train"], "extra_all": D[D.phase == "train_extra"],
       "extra_top_score": D[D.group == "extra_top_score"], "extra_random": D[D.group == "extra_random"]}
SUBNOTE = {"main_all": "main tự nhiên, train+val+test GỘP (chỉ mô tả)", "main_train": "main tự nhiên, chỉ train",
           "extra_all": "train_extra GỘP hai tầng (chọn theo điểm, lệch)", "extra_top_score": "train_extra tầng top_score",
           "extra_random": "train_extra tầng random"}
GROUPS = {g: D[D.group == g] for g in GORDER}
GROUPS_P = dict(GROUPS) | {"main_all": SUB["main_all"], "extra_all": SUB["extra_all"]}  # pooled rows are named as such
NUM["n_rows"] = {g: len(d) for g, d in GROUPS_P.items()}

# ================================================================== 1. inventory
print("1. inventory")
STRUCT = {
    "reason": "chỉ có khi label = I (lý do không đủ thông tin); thiếu ở nhãn 0 và 1 là cấu trúc",
    "obstacles": "chỉ có khi annotator chọn Bị chặn (1); thiếu ở nhãn 0 và I là cấu trúc",
    "note": "ghi chú tự do, hầu như để trống", "difficult": "cờ khó, chỉ một ít người dùng",
    "stratum": "chỉ có ở phần train_extra", "score": "chỉ có ở phần train_extra (điểm bộ chọn ảnh, không phải nhãn)",
    "label_v1": "chỉ có ở train_extra", "sampling_stratum": "chỉ có ở pilot", "position_group": "pilot_v2 không có vị trí nhóm",
    "label2": "chỉ có khi ảnh có người gán thứ hai", "annotator2": "chỉ có khi ảnh có người gán thứ hai",
    "reason2": "chỉ có khi người gán thứ hai chọn I", "obstacles2": "chỉ có khi người thứ hai chọn Bị chặn",
    "reason1": "chỉ có khi người đầu chọn I", "obstacles1": "chỉ có khi người đầu chọn Bị chặn", "role2": "chỉ có khi có người thứ hai",
    "rank": "chỉ có ở ảnh đã xếp hạng trong kho", "markets": "đường không có chợ gần thì để trống", "schools": "đường không có trường gần thì để trống",
    "day": "", "years": "", "creators": ""}
inv_t, inv_c = [], []
for name, (path, df) in TABLES.items():
    inv_t.append(dict(table=name, path=path, rows=len(df), columns=df.shape[1]))
    for c in df.columns:
        m = int(df[c].isna().sum())
        inv_c.append(dict(table=name, column=c, dtype=str(df[c].dtype), n_missing=m, share_missing=m / len(df),
                          structural_note=STRUCT.get(c, "") if m else ""))
INV_C = pd.DataFrame(inv_c)
wcsv(pd.DataFrame(inv_t), "inventory_tables.csv")
wcsv(INV_C, "inventory_columns.csv")
NUM["inventory"] = {"tables": {r["table"]: dict(rows=r["rows"], columns=r["columns"]) for r in inv_t},
                    "columns_with_missing": INV_C[INV_C.n_missing > 0][["table", "column", "n_missing"]].to_dict("records")}
# structural-missingness check: reason vs label, obstacles vs label
NUM["structural_missing"] = {
    "main_labels_v1: label I rows with reason missing": int(((LAB.label == "I") & LAB.reason.isna()).sum()),
    "main_labels_v1: label 0/1 rows with reason present": int(((LAB.label != "I") & LAB.reason.notna()).sum()),
    "train_extra_labels_v2: label I rows with reason missing": int(((EXL.label == "I") & EXL.reason.isna()).sum()),
    "train_extra_labels_v2: label 0/1 rows with reason present": int(((EXL.label != "I") & EXL.reason.notna()).sum()),
    "main annotations: label 1 with obstacles missing": int(((ANN_M.label == "1") & ANN_M.obstacles.isna()).sum()),
    "main annotations: label 0/I with obstacles present": int(((ANN_M.label != "1") & ANN_M.obstacles.notna()).sum()),
    "train_extra annotations: label 1 with obstacles missing": int(((ANN_X.label == "1") & ANN_X.obstacles.isna()).sum()),
    "train_extra annotations: label 0/I with obstacles present": int(((ANN_X.label != "1") & ANN_X.obstacles.notna()).sum())}

# ================================================================== 2. descriptive statistics
print("2. descriptive statistics")
rows = []
for var in ["brightness", "dist_to_street_m", "lat", "lon", "travel_bearing", "score"]:
    for g, d in GROUPS_P.items():
        if var == "score" and not g.startswith("extra"):
            continue
        rows.append(dict(variable=var, group=g, group_name=GNAME.get(g, g), **desc(d[var])))
# labelling seconds per annotation (main: by split of the item; train_extra: by stratum)
ANN_M["grp"] = "main_" + ANN_M.split
ANN_X["grp"] = "extra_" + ANN_X.stratum
SEC = {**{g: ANN_M[ANN_M.grp == g].seconds for g in ["main_train", "main_val", "main_test"]}, "main_all": ANN_M.seconds,
       **{g: ANN_X[ANN_X.grp == g].seconds for g in ["extra_top_score", "extra_random"]}, "extra_all": ANN_X.seconds}
for g, s in SEC.items():
    rows.append(dict(variable="seconds_per_annotation", group=g, group_name=GNAME.get(g, g), **desc(s)))
DESC = pd.DataFrame(rows)
wcsv(DESC, "desc_numeric.csv")
tail = []
for g, s in SEC.items():
    tail.append(dict(group=g, n=len(s), p05=s.quantile(.05), p50=s.median(), p90=s.quantile(.9), p99=s.quantile(.99),
                     max=s.max(), n_over_60s=int((s > 60).sum()), n_over_600s=int((s > 600).sum()), n_over_3600s=int((s > 3600).sum()),
                     mean_over_median=s.mean() / s.median()))
TAIL = pd.DataFrame(tail)
wcsv(TAIL, "seconds_heavy_tail.csv")
NUM["seconds"] = {"note": "per annotation, heavy-tailed (a task left open inflates the mean); use median/IQR. Pilot annotations are not in the specified tables: chưa đo",
                  "by_group": TAIL.set_index("group").to_dict("index")}
NUM["desc_numeric"] = {f"{r.variable}|{r.group}": {k: getattr(r, k) for k in ["n", "mean", "median", "variance", "std", "min", "q1", "q3", "max", "iqr"]}
                       for r in DESC.itertuples()}

cat_rows = []
for var in ["creator", "year", "month", "hour", "street_id", "highway", "source"]:
    for g, d in GROUPS_P.items():
        vc = d[var].value_counts(dropna=False).sort_index() if var in ("year", "month", "hour") else d[var].value_counts(dropna=False)
        for k, v in vc.items():
            cat_rows.append(dict(variable="label_source" if var == "source" else var, group=g, category=k, n=int(v), share=v / len(d)))
CAT = pd.DataFrame(cat_rows)
wcsv(CAT, "cat_distributions.csv")
sp = D.groupby(["phase", "street_id"]).size().rename("crops").reset_index()
NUM["crops_per_street"] = {ph: desc(sp[sp.phase == ph].crops) | {"n_streets": int((sp.phase == ph).sum())} for ph in sp.phase.unique()}
hv = D.groupby(["phase", "hour"]).size().unstack(0).fillna(0).astype(int)
NUM["stamped_hour_share_06_18"] = {ph: float(D[(D.phase == ph) & D.hour.between(6, 18)].shape[0] / (D.phase == ph).sum()) for ph in D.phase.unique()}
NUM["captured_year_share"] = {g: D[D.group == g].year.value_counts(normalize=True).sort_index().round(4).to_dict() for g in GORDER}

# ================================================================== 3. label distribution
print("3. label distribution")


def boot_blocked(d, rng):
    """street-cluster bootstrap interval for blocked share among usable crops."""
    u = d[d.usable].groupby("street_id").agg(k=("blocked", "sum"), n=("blocked", "size"))
    if len(u) < 2:
        return (np.nan, np.nan, len(u))
    idx = rng.integers(0, len(u), (B, len(u)))
    s = u.k.to_numpy()[idx].sum(1) / u.n.to_numpy()[idx].sum(1)
    return (np.percentile(s, 2.5), np.percentile(s, 97.5), len(u))


def label_row(d, name, rng=None):
    n = len(d)
    n0, n1, nI = [int((d.label == k).sum()) for k in "01I"]
    u = n0 + n1
    pu = wilson(n1, u)
    pa = wilson(n1, n)
    pi = wilson(nI, n)
    r = dict(group=name, n=n, n0=n0, n1=n1, nI=nI, share0=n0 / n, share1=n1 / n, shareI=nI / n, usable=u,
             blocked_share_usable=pu[0], bu_lo=pu[1], bu_hi=pu[2], blocked_share_all=pa[0], ba_lo=pa[1], ba_hi=pa[2],
             I_share=pi[0], I_lo=pi[1], I_hi=pi[2], imbalance_0_to_1=n0 / n1 if n1 else np.nan)
    if rng is not None:
        lo, hi, ns = boot_blocked(d, np.random.default_rng(SEED))
        r.update(bu_cluster_lo=lo, bu_cluster_hi=hi, n_streets=ns)
    return r


LC = pd.DataFrame([label_row(d, g, True) for g, d in GROUPS_P.items()])
LC["group_name"] = LC.group.map(lambda g: GNAME.get(g, {"main_all": "Main tự nhiên – 3 split GỘP", "extra_all": "Train-extra – 2 tầng GỘP"}.get(g)))
wcsv(LC, "label_counts_by_group.csv")
NUM["labels_by_group"] = LC.set_index("group").drop(columns="group_name").to_dict("index")
NUM["labels_by_group_note"] = ("bu_* = Wilson 95% for blocked/usable; ba_* = Wilson for blocked/all crops; bu_cluster_* = street-cluster bootstrap "
                               f"(B={B}); main_val has 3 streets, main_test 4, pilot 3: cluster interval is only indicative; extra_* are selected by a model score, not natural")
# per split (descriptive); train/val/test over all phases and main only
rows = []
for sp_ in ["train", "val", "test"]:
    rows.append(label_row(D[(D.phase == "main") & (D.split == sp_)], f"main tự nhiên – {sp_}"))
    if sp_ == "train":
        rows.append(label_row(D[D.group == "pilot"], "pilot – train"))
        rows.append(label_row(D[D.phase == "train_extra"], "train_extra – train"))
        rows.append(label_row(D[D.split == "train"], "train, TẤT CẢ phase gộp (main+pilot+extra)"))
rows.append(label_row(D[D.phase == "main"], "main tự nhiên, 3 split gộp"))
rows.append(label_row(D[D.phase.isin(["main", "pilot"])], "main+pilot (gộp, = tổng nhãn đợt 1)"))
SPL = pd.DataFrame(rows)
wcsv(SPL, "label_counts_by_split.csv")
NUM["labels_by_split"] = SPL.set_index("group").to_dict("index")
# pilot by sampling stratum
PS = pd.DataFrame([label_row(d, f"pilot_stratum={k}") for k, d in GROUPS["pilot"].groupby("pilot_stratum")])
wcsv(PS, "label_counts_pilot_by_stratum.csv")
# train composition before/after adding train_extra
Dtr = D[D.split == "train"]
comps = {"T1 main train": ["main_train"], "T2 main train + pilot": ["main_train", "pilot"],
         "T3 main train + extra (top_score + random)": ["main_train", "extra_top_score", "extra_random"],
         "T4 main train + pilot + extra (đủ, train hiện tại)": ["main_train", "pilot", "extra_top_score", "extra_random"],
         "T5 main train + pilot + extra random": ["main_train", "pilot", "extra_random"],
         "T6 main train + pilot + extra top_score": ["main_train", "pilot", "extra_top_score"]}
rows = []
for name, gs in comps.items():
    d = Dtr[Dtr.group.isin(gs)]
    r = label_row(d, name)
    pos = d[d.blocked]
    for g in ["main_train", "pilot", "extra_top_score", "extra_random"]:
        r[f"blocked_from_{g}"] = int((pos.group == g).sum())
    r["share_blocked_from_extra"] = (r["blocked_from_extra_top_score"] + r["blocked_from_extra_random"]) / max(1, r["n1"])
    rows.append(r)
TC = pd.DataFrame(rows)
wcsv(TC, "train_composition.csv")
NUM["train_composition"] = TC.set_index("group").to_dict("index")
NUM["train_composition_note"] = "Wilson intervals treat crops as independent; the composition is not a natural sample for T3-T6 (extra selected by model score)"

# per street
rows = []
sp_map = pd.concat([D.drop_duplicates("street_id").set_index("street_id").split])
for key, d in [("main", D[D.phase == "main"]), ("pilot", D[D.group == "pilot"]), ("extra_all", D[D.phase == "train_extra"]),
               ("extra_top_score", D[D.group == "extra_top_score"]), ("extra_random", D[D.group == "extra_random"])]:
    for s, x in d.groupby("street_id"):
        r = label_row(x, s)
        r.update(group_set=key, street_id=s, split=x.split.iloc[0], highway=x.highway.iloc[0])
        rows.append(r)
ST = pd.DataFrame(rows)
ST = ST[["group_set", "street_id", "split", "highway"] + [c for c in ST.columns if c not in ("group_set", "street_id", "split", "highway", "group")]]
wcsv(ST, "labels_by_street.csv")
# blocked share by categorical attribute
rows = []
for sub, d in SUB.items():
    for var in ["creator", "year", "highway", "month"]:
        for k, x in d.groupby(var):
            r = label_row(x, k)
            rows.append(dict(subset=sub, variable=var, category=k, **{c: r[c] for c in ["n", "n0", "n1", "nI", "usable", "blocked_share_usable", "bu_lo", "bu_hi", "I_share"]}))
wcsv(pd.DataFrame(rows), "label_by_category.csv")

# reasons for I
rows = []
for g, d in GROUPS_P.items():
    di = d[d.label == "I"]
    vc = di.reason.fillna("(thiếu lý do)").value_counts()
    for k in REASONS + ["(thiếu lý do)"]:
        rows.append(dict(group=g, reason=k, n=int(vc.get(k, 0)), n_I=len(di), share_of_I=vc.get(k, 0) / len(di)))
RS = pd.DataFrame(rows)
wcsv(RS, "reasons_I.csv")
NUM["reasons_I"] = {g: RS[RS.group == g].set_index("reason").n.to_dict() for g in GROUPS_P}


# obstacle tags on blocked crops
def tagset(s):
    return set(s.split("|")) if isinstance(s, str) and s else set()


def tags_item_union(ann, items):
    """item -> union of tags over annotations that gave label 1 (each item counts once per tag)."""
    u = ann[(ann.label == "1") & ann.item.isin(items)].groupby("item").obstacles.apply(lambda s: set().union(*[tagset(x) for x in s]))
    return u.reindex(list(items)).apply(lambda x: x if isinstance(x, set) else set())


rows = []
obs_groups = {"main_train": D[(D.group == "main_train") & D.blocked], "main_val": D[(D.group == "main_val") & D.blocked],
              "main_test": D[(D.group == "main_test") & D.blocked], "main_all": D[(D.phase == "main") & D.blocked],
              "extra_top_score": D[(D.group == "extra_top_score") & D.blocked], "extra_random": D[(D.group == "extra_random") & D.blocked],
              "extra_all": D[(D.phase == "train_extra") & D.blocked]}
for g, d in obs_groups.items():
    ann = ANN_M if g.startswith("main") else ANN_X
    ts = tags_item_union(ann, d.item)
    notag = int((ts.apply(len) == 0).sum())
    for t in TAGS:
        n = int(ts.apply(lambda s: t in s).sum())
        rows.append(dict(group=g, basis="item: nhãn cuối = 1; thẻ gộp (union) từ các lượt gán 1 của ảnh", tag=t, n_with_tag=n, denominator=len(d),
                         share=n / len(d), n_items_without_any_tag=notag))
    rows.append(dict(group=g, basis="item: nhãn cuối = 1; thẻ gộp (union) từ các lượt gán 1 của ảnh", tag="(không có thẻ)", n_with_tag=notag,
                     denominator=len(d), share=notag / len(d), n_items_without_any_tag=notag))
# per-annotation basis (all annotations with label 1; matches how docs count tags)
for g, ann in [("main_all", ANN_M), ("extra_all (nhãn v1)", ANN_X)]:
    a1 = ann[ann.label == "1"]
    for t in TAGS:
        n = int(a1.obstacles.apply(lambda s: t in tagset(s)).sum())
        rows.append(dict(group=g, basis="lượt gán: mọi lượt có label 1 (nhãn v1 với train_extra)", tag=t, n_with_tag=n, denominator=len(a1),
                         share=n / len(a1), n_items_without_any_tag=int(a1.obstacles.isna().sum())))
OB = pd.DataFrame(rows)
wcsv(OB, "obstacle_tags.csv")
NUM["obstacle_tags"] = {f"{r.group}|{r.tag}|{r.basis[:4]}": dict(n=r.n_with_tag, denominator=r.denominator, share=r.share) for r in OB.itertuples()}
NUM["obstacle_tags_note"] = ("Multi-label: shares do not sum to 1. Main double-labelled items: a tag counts once per item if ANY annotator who labelled it 1 chose it. "
                             "Pilot: chưa đo (no per-annotation table with tags among the specified inputs).")

# per-annotator label shares
rows = []
for src, ann, grpcol in [("main", ANN_M, "role"), ("train_extra", ANN_X, "stratum")]:
    for (a, k), x in ann.groupby(["annotator", grpcol]):
        n = len(x)
        r = dict(source=src, annotator=a, by=grpcol, level=k, n=n, median_s=x.seconds.median())
        for lab in "01I":
            r[f"n{lab}"] = int((x.label == lab).sum())
            r[f"share{lab}"] = r[f"n{lab}"] / n
        rows.append(r)
    for a, x in ann.groupby("annotator"):
        n = len(x)
        r = dict(source=src, annotator=a, by="all", level="all", n=n, median_s=x.seconds.median())
        for lab in "01I":
            r[f"n{lab}"] = int((x.label == lab).sum())
            r[f"share{lab}"] = r[f"n{lab}"] / n
        b = wilson(r["n1"], r["n0"] + r["n1"])
        r.update(blocked_among_usable=b[0], bu_lo=b[1], bu_hi=b[2])
        rows.append(r)
AN = pd.DataFrame(rows)
wcsv(AN, "annotator_label_shares.csv")
chi = {}
for name, tab in [("main role=train_single (5 annotators, one per item)", ANN_M[ANN_M.role == "train_single"]),
                  ("train_extra all (v1 labels)", ANN_X), ("train_extra random stratum (v1 labels)", ANN_X[ANN_X.stratum == "random"])]:
    c2, p, dof, _ = stats.chi2_contingency(pd.crosstab(tab.annotator, tab.label))
    chi[name] = dict(chi2=c2, dof=dof, p=p, n=len(tab))
NUM["annotator_chi2"] = chi
NUM["annotator_note"] = ("Main annotations: each annotator labels a different mix (test: Học+Loan, val: Minh+Khải, train: all 5), so shares per annotator over all roles "
                         "are confounded by split; role=train_single and train_extra are randomly assigned. train_extra labels are the v1 labels (before cross-check).")
NUM["annotator_shares"] = AN[AN.by == "all"].set_index(["source", "annotator"])[["n", "share0", "share1", "shareI", "median_s"]].round(4).reset_index().to_dict("records")

# ================================================================== 4. relationships
print("4. relationships between attributes")
NUMVARS = ["brightness", "dist_to_street_m", "lat", "lon", "year", "travel_bearing"]
spear_pairs = []
SP, VIF = {}, []
for sub, d in SUB.items():
    cols = NUMVARS + (["score"] if sub.startswith("extra") else [])
    m = d[cols].astype(float).corr(method="spearman")
    SP[sub] = m
    wcsv(m.reset_index().rename(columns={"index": "variable"}), f"spearman_{sub}.csv")
    X = d[cols].astype(float).dropna()
    Z = ((X - X.mean()) / X.std(ddof=0)).to_numpy()
    for j, c in enumerate(cols):
        others = np.delete(Z, j, axis=1)
        A = np.column_stack([np.ones(len(Z)), others])
        beta, *_ = np.linalg.lstsq(A, Z[:, j], rcond=None)
        r2 = 1 - ((Z[:, j] - A @ beta) ** 2).sum() / ((Z[:, j] - Z[:, j].mean()) ** 2).sum()
        VIF.append(dict(subset=sub, variable=c, vif=1 / (1 - r2), r2=r2, n=len(Z)))
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            spear_pairs.append(dict(subset=sub, a=a, b=b, rho=m.loc[a, b]))
VIF = pd.DataFrame(VIF)
wcsv(VIF, "vif.csv")
SPP = pd.DataFrame(spear_pairs)
SPP["abs_rho"] = SPP.rho.abs()
NUM["spearman_top_pairs"] = {s: SPP[SPP.subset == s].sort_values("abs_rho", ascending=False).head(5)[["a", "b", "rho"]].round(3).to_dict("records") for s in SUB}
NUM["vif"] = {s: VIF[VIF.subset == s].set_index("variable").vif.round(3).to_dict() for s in SUB}
NUM["vif_note"] = ("travel_bearing is circular (0-360), entered raw as in the Spearman matrix; lat/lon/street are structurally linked "
                   "(crops lie along streets). VIF > 5 would indicate multicollinearity.")


def auc_of(x, y):
    n1, n0 = int(y.sum()), int((~y).sum())
    r = stats.rankdata(x)
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def boot_auc(x, y, groups, seed):
    codes, uniq = pd.factorize(groups)
    idxs = [np.where(codes == g)[0] for g in range(len(uniq))]
    rng = np.random.default_rng(seed)
    res = []
    for _ in range(B):
        ii = np.concatenate([idxs[g] for g in rng.integers(0, len(uniq), len(uniq))])
        yy = y[ii]
        if yy.all() or (~yy).all():
            continue
        res.append(auc_of(x[ii], yy))
    return np.percentile(res, [2.5, 97.5]) if res else (np.nan, np.nan)


def v_from_table(t):
    t = t[t.sum(1) > 0][:, t.sum(0) > 0]
    r, c = t.shape
    n = t.sum()
    if r < 2 or c < 2 or n < 2:
        return np.nan, np.nan, np.nan
    e = np.outer(t.sum(1), t.sum(0)) / n
    chi2 = ((t - e) ** 2 / e).sum()
    phi2 = max(0.0, chi2 / n - (r - 1) * (c - 1) / (n - 1))
    rc, kc = r - (r - 1) ** 2 / (n - 1), c - (c - 1) ** 2 / (n - 1)
    return math.sqrt(phi2 / min(kc - 1, rc - 1)), stats.chi2.sf(chi2, (r - 1) * (c - 1)), (r - 1) * (c - 1)


def boot_v(codes, y, groups, K, seed):
    gcodes, uniq = pd.factorize(groups)
    idxs = [np.where(gcodes == g)[0] for g in range(len(uniq))]
    rng = np.random.default_rng(seed)
    res = []
    for _ in range(B):
        ii = np.concatenate([idxs[g] for g in rng.integers(0, len(uniq), len(uniq))])
        t = np.bincount(codes[ii] * 2 + y[ii].astype(int), minlength=2 * K).reshape(K, 2).astype(float)
        v = v_from_table(t)[0]
        if not np.isnan(v):
            res.append(v)
    return np.percentile(res, [2.5, 97.5]) if res else (np.nan, np.nan)


ANUM = NUMVARS + ["bear_sin", "bear_cos"]
rows_n, rows_c = [], []
for sub, d0 in SUB.items():
    for target in ["blocked_vs_passable", "I_vs_usable"]:
        d = d0[d0.usable] if target == "blocked_vs_passable" else d0
        y = (d.blocked if target == "blocked_vs_passable" else (d.label == "I")).to_numpy()
        for var in ANUM + (["score"] if sub.startswith("extra") else []):
            x = d[var].to_numpy(float)
            ok = ~np.isnan(x)
            auc = auc_of(x[ok], y[ok])
            lo, hi = boot_auc(x[ok], y[ok], d.street_id.to_numpy()[ok], SEED)
            eff = abs(2 * auc - 1)
            read = ("không phân biệt được (CI chứa 0,5)" if lo <= 0.5 <= hi else ("yếu" if eff < 0.10 else "có tín hiệu"))
            rows_n.append(dict(subset=sub, target=target, variable=var, n=int(ok.sum()), n_pos=int(y[ok].sum()), auc_pos_higher=auc,
                               effect_abs_2auc_minus1=eff, point_biserial_r=np.corrcoef(x[ok], y[ok])[0, 1],
                               p_mwu_iid_optimistic=stats.mannwhitneyu(x[ok][y[ok]], x[ok][~y[ok]]).pvalue, auc_lo_cluster=lo, auc_hi_cluster=hi,
                               n_streets=d.street_id.nunique(), reading=read,
                               note="vòng (0-360): AUC thô không có nghĩa rõ, xem bear_sin/bear_cos" if var == "travel_bearing" else ""))
        cats = ["street_id", "creator", "year", "highway", "month"] + (["split"] if sub == "main_all" else []) + (["stratum"] if sub == "extra_all" else [])
        for var in cats:
            codes, uniq = pd.factorize(d[var])
            K = len(uniq)
            t = np.bincount(codes * 2 + y.astype(int), minlength=2 * K).reshape(K, 2).astype(float)
            v, p, dof = v_from_table(t)
            lo = hi = np.nan
            if var in ("creator", "year", "highway", "month"):
                lo, hi = boot_v(codes, y, d.street_id.to_numpy(), K, SEED)
            read = "rất nhỏ (<0,1)" if v < 0.1 else ("nhỏ-vừa (0,1-0,3)" if v < 0.3 else "khá lớn (>=0,3)")
            note = ""
            if var == "street_id":
                note = "bias-corrected V; nhiều mức, bảng thưa; street là cụm nên chỉ dùng như mức độ khác biệt giữa đường, không bootstrap"
            if var == "highway":
                note = "highway hằng số trong mỗi đường: hiệu ứng đường lớn/nhỏ lẫn với đường cụ thể"
            if var in ("split", "stratum"):
                note = "split gộp theo đường (3 val, 4 test, 10 train)" if var == "split" else "tầng chọn theo điểm bộ chọn ảnh: liên hệ nhãn là do thiết kế"
            rows_c.append(dict(subset=sub, target=target, variable=var, n=len(d), n_levels=K, cramers_v_bc=v, chi2_p_iid_optimistic=p, dof=dof,
                               v_lo_cluster=lo, v_hi_cluster=hi, reading=read, note=note))
AUCT, CRAMT = pd.DataFrame(rows_n), pd.DataFrame(rows_c)
wcsv(AUCT, "assoc_numeric.csv")
wcsv(CRAMT, "assoc_categorical.csv")
top = AUCT[AUCT.subset.isin(["main_all", "extra_all"]) & ~AUCT.variable.isin(["travel_bearing"])].sort_values("effect_abs_2auc_minus1", ascending=False)
NUM["assoc_numeric_top_effects"] = top.head(6)[["subset", "target", "variable", "auc_pos_higher", "auc_lo_cluster", "auc_hi_cluster", "n"]].round(4).to_dict("records")
topc = CRAMT[CRAMT.subset.isin(["main_all", "extra_all"]) & ~CRAMT.variable.isin(["street_id", "split", "stratum"])].sort_values("cramers_v_bc", ascending=False)
NUM["assoc_categorical_top_effects"] = topc.head(6)[["subset", "target", "variable", "cramers_v_bc", "v_lo_cluster", "v_hi_cluster", "n"]].round(4).to_dict("records")
NUM["assoc_street_v"] = CRAMT[CRAMT.variable == "street_id"].set_index(["subset", "target"]).cramers_v_bc.round(4).reset_index().to_dict("records")
NUM["assoc_note"] = ("Crops are clustered by street: iid p-values (p_*_optimistic) are too small; use effect sizes and the street-cluster bootstrap intervals "
                     f"(B={B}, resampling streets with replacement). 'reading' is a heuristic: CI of AUC contains 0.5 -> no separation; |2AUC-1|<0.10 -> weak; else signal. "
                     "Metadata are not model inputs. main_all pools val/test and is descriptive only; main_train is the train-only view.")

# ================================================================== 5. consistency / validity checks
print("5. consistency checks")
CHK = []


def chk(name, ok, violations, detail=""):
    CHK.append(dict(check=name, result="PASS" if ok else "FAIL", violations=violations, detail=detail))


KEY = {"main": ("main_v1.csv", Lm), "pilot": ("pilot_v2.csv", Lp), "extra": ("train_extra_v1.csv", EXL)}
# 1. unique ids
for nm, df in [("main_labels_v1 (main+pilot)", LAB), ("train_extra_labels_v2", EXL)]:
    d = int(df.item.duplicated().sum())
    chk(f"item unique within {nm}", d == 0, d)
allit = pd.concat([Lm.item, Lp.item, EXL.item])
chk("item unique across main / pilot / train_extra labels", not allit.duplicated().any(), int(allit.duplicated().sum()), f"{len(allit)} ids, {allit.nunique()} distinct")
chk("item unique within each manifest and across them", not pd.concat(list(m.item for m in MAN.values())).duplicated().any(),
    int(pd.concat(list(m.item for m in MAN.values())).duplicated().sum()))
# 2. join 1:1
for k, (f, lab) in KEY.items():
    m = MAN[k]
    a, b = set(lab.item), set(m.item)
    chk(f"labels({k}) <-> {f}: every label row joins exactly one manifest row and vice versa", a == b and not m.item.duplicated().any(),
        len(a - b) + len(b - a), f"labels {len(lab)}, manifest {len(m)}, labels-not-in-manifest {len(a - b)}, manifest-not-in-labels {len(b - a)}")
# 3. split / street agree
yx = {s["id"]: s["split"] for s in YM}
yxe = {s["id"]: s["split"] for s in YX}
for k, (f, lab) in KEY.items():
    x = lab.merge(MAN[k][["item", "split", "street_id"]], on="item", suffixes=("", "_m"))
    bad = x[(x.split != x.split_m) | (x.street_id != x.street_id_m)]
    chk(f"split and street_id agree labels vs manifest ({k})", len(bad) == 0, len(bad))
    ys = yxe if k == "extra" else yx
    x["ysplit"] = x.street_id.map(ys)
    bad = x[x.ysplit.isna() | (x.ysplit != x.split)]
    chk(f"split/street_id agree labels vs configs/{'streets_train_extra' if k == 'extra' else 'streets_v1'}.yaml ({k})", len(bad) == 0, len(bad),
        f"streets not in yaml or split differs: {sorted(bad.street_id.unique())[:5]}")
chk("streets_v1.yaml has 17 streets (4 test, 3 val, 10 train)", len(YM) == 17 and pd.Series([s["split"] for s in YM]).value_counts().to_dict() == {"train": 10, "test": 4, "val": 3}, 0)
chk("streets_train_extra.yaml has 75 streets, all train", len(YX) == 75 and all(s["split"] == "train" for s in YX), 0)
# 4. street in one split only
ss = D.groupby("street_id").split.nunique()
chk("no street_id in more than one split (all phases)", (ss <= 1).all(), int((ss > 1).sum()), str(list(ss[ss > 1].index)))
both = set(MAN["extra"].street_id) & set(MAN["main"].street_id)
chk("no street shared between train_extra and main", not both, len(both), str(sorted(both)))
nm_ext = {s.split("#")[0] for s in MAN["extra"].street_id} & {s.split("#")[0] for s in D[D.split.isin(["val", "test"])].street_id}
chk("no train_extra street shares a base name with a val/test street", not nm_ext, len(nm_ext), str(sorted(nm_ext)))
# 5. position_group
pg = pd.concat([MAN["main"][["item", "position_group", "split"]], MAN["extra"][["item", "position_group", "split"]]])
n_sp = pg.groupby("position_group").split.nunique()
chk("no position_group shared between splits (main + train_extra)", (n_sp <= 1).all(), int((n_sp > 1).sum()))
pm, px = MAN["main"], MAN["extra"]
chk("no position_group shared between main and train_extra (info)", not (set(pm.position_group) & set(px.position_group)), len(set(pm.position_group) & set(px.position_group)))
chk("position_group duplicates within main / train_extra (info: several panos per 25 m position are allowed)", True,
    int(pm.position_group.duplicated().sum() + px.position_group.duplicated().sum()),
    f"main {int(pm.position_group.duplicated().sum())}, extra {int(px.position_group.duplicated().sum())}")
# pilot has no position_group: approximate by distance to the nearest main crop on the same street
xm = np.column_stack(to_xy(pm.lon.to_numpy(), pm.lat.to_numpy()))
dmin = []
for s, g in MAN["pilot"].groupby("street_id"):
    tree = cKDTree(np.column_stack(to_xy(pm[pm.street_id == s].lon.to_numpy(), pm[pm.street_id == s].lat.to_numpy())))
    dmin += list(tree.query(np.column_stack(to_xy(g.lon.to_numpy(), g.lat.to_numpy())))[0])
dmin = np.array(dmin)
NUM["pilot_to_main_distance_m"] = dict(min=dmin.min(), p5=np.percentile(dmin, 5), median=np.median(dmin), n_within_5m=int((dmin < 5).sum()), n_within_25m=int((dmin < 25).sum()),
                                       note="pilot_v2 has no position_group; distance to nearest main crop of the same street is the only proxy (not the 25 m position key)")
chk("pilot crops vs main crops: none within 5 m (proxy for 'no shared position', pilot has no position_group)", (dmin < 5).sum() == 0, int((dmin < 5).sum()),
    f"min distance {dmin.min():.2f} m, within 25 m: {int((dmin < 25).sum())} of {len(dmin)}")
# 6. parent pano
for k, m in MAN.items():
    d = int(m.parent_pano_id.duplicated().sum())
    chk(f"parent_pano_id unique within manifest {k}", d == 0, d)
pairs = [("main", "pilot"), ("main", "extra"), ("pilot", "extra")]
for a, b in pairs:
    s = set(MAN[a].parent_pano_id) & set(MAN[b].parent_pano_id)
    chk(f"parent_pano_id shared between {a} and {b}", not s, len(s))
chk("collection_status: 3,057 panos, ok 2,999 / night 58; ok ids == main manifest parents",
    len(STAT) == 3057 and STAT.status.value_counts().to_dict() == {"ok": 2999, "night": 58} and set(STAT[STAT.status == "ok"].id) == set(MAN["main"].parent_pano_id), 0,
    str(STAT.status.value_counts().to_dict()))
chk("candidate pool 5,074 (ok 5,035 / night 38 / near_duplicate 1); train_extra parents subset of pool ok",
    len(POOL) == 5074 and POOL.status.value_counts().to_dict() == {"ok": 5035, "night": 38, "near_duplicate": 1} and set(MAN["extra"].parent_pano_id) <= set(POOL[POOL.status == "ok"].id), 0,
    str(POOL.status.value_counts().to_dict()))
# 7. values
for nm, df in [("main_labels_v1", LAB), ("train_extra_labels_v2", EXL), ("train_extra label_v1", EXL.label_v1.to_frame("label")),
               ("main annotations", ANN_M), ("train_extra annotations", ANN_X), ("main_items label_final", ITEMS_M.rename(columns={"label_final": "label"}))]:
    bad = int((~df.label.isin(["0", "1", "I"])).sum())
    chk(f"label values in {{0,1,I}} ({nm})", bad == 0, bad)
for nm, df in [("main_labels_v1", LAB), ("train_extra_labels_v2", EXL)]:
    a, b = int(((df.label == "I") & df.reason.isna()).sum()), int(((df.label != "I") & df.reason.notna()).sum())
    miss = df[(df.label == "I") & df.reason.isna()].groupby(["phase", "source"]).size().to_dict()
    tot = df[df.label == "I"].groupby(["phase", "source"]).size().to_dict()
    chk(f"reason present iff label I ({nm}) [structural: adjudicated / pilot-review labels carry no reason]", a + b == 0, a + b,
        f"I without reason {a}, non-I with reason {b}; I-without-reason by (phase, source) {miss} of I {tot}")
    NUM["structural_missing"][f"{nm}: I without reason by (phase, source) / all I"] = {f"{k[0]}|{k[1]}": f"{v}/{tot[k]}" for k, v in miss.items()}
for nm, ann in [("main annotations", ANN_M), ("train_extra annotations", ANN_X)]:
    v = int(((ann.label != "1") & ann.obstacles.notna()).sum())
    chk(f"obstacles present only when annotation label = 1 ({nm}) [stale tags after a label change]", v == 0, v,
        f"annotations with label 0/I but obstacle tags: {v} of {len(ann)}; label 1 without tags: {int(((ann.label == '1') & ann.obstacles.isna()).sum())}")
chk("reason values in the 4 known categories", D.reason.dropna().isin(REASONS).all(), int((~D.reason.dropna().isin(REASONS)).sum()))
chk("label source values known", D.source.isin(["single", "agreed", "adjudicated_proposal", "pilot_review_proposal", "adjudicated_phuc", "pilot_review_phuc", "cross_check"]).all(), 0, str(D.source.value_counts().to_dict()))
chg = EXL[EXL.label != EXL.label_v1]
chk("train_extra v2 differs from v1 exactly where source = cross_check (17 labels)", len(chg) == 17 and (chg.source == "cross_check").all() and (EXL[EXL.source == "cross_check"].label != EXL[EXL.source == "cross_check"].label_v1).all(),
    abs(len(chg) - 17), f"changed {len(chg)}; cross_check rows {(EXL.source == 'cross_check').sum()}")
mi = ITEMS_M.merge(Lm[["item", "label"]], on="item", how="outer", indicator=True)
chk("main_items.label_final == main_labels_v1.label (main phase)", (mi._merge == "both").all() and (mi.label_final == mi.label).all(), int((mi._merge != "both").sum() + (mi.label_final != mi.label).sum()))
tv = ANN_X.merge(EXL[["item", "label_v1"]], on="item")
chk("train_extra per-annotation label == label_v1 of v2 file", len(tv) == 2000 and (tv.label == tv.label_v1).all(), int((tv.label != tv.label_v1).sum()))
# 8. side/yaw
for k, m in MAN.items():
    chk(f"side == R and yaw_off_from_travel == 60 ({k})", (m.side == "R").all() and (m.yaw_off_from_travel == 60).all(), int(((m.side != "R") | (m.yaw_off_from_travel != 60)).sum()))
    d = int(((m.yaw < -180) | (m.yaw > 180)).sum() + ((m.travel_bearing < 0) | (m.travel_bearing >= 360)).sum())
    chk(f"yaw in [-180,180], travel_bearing in [0,360) ({k})", d == 0, d)
# 9. bbox
S_, W_, N_, E_ = BBOX
bb = []
for k, m in MAN.items():
    v = m[(m.lat < S_) | (m.lat > N_) | (m.lon < W_) | (m.lon > E_)]
    bb.append(v.assign(manifest=k))
    chk(f"lat/lon inside study bbox 10.745-10.815 N, 106.650-106.725 E ({k})", len(v) == 0, len(v))
BBV = pd.concat(bb)
wcsv(BBV[["manifest", "item", "street_id", "split", "lat", "lon", "parent_pano_id"]] if len(BBV) else pd.DataFrame(columns=["manifest", "item", "street_id", "split", "lat", "lon"]), "bbox_violations.csv")
# 10. brightness, licence, file naming, crop id <-> file
for k, m in MAN.items():
    chk(f"brightness >= 90 for all kept crops ({k})", (m.brightness >= 90).all(), int((m.brightness < 90).sum()), f"min {m.brightness.min()}, max {m.brightness.max()}")
    chk(f"licence constant ({k})", m.licence.nunique() == 1, int(m.licence.nunique() - 1), str(m.licence.unique()))
    folder = Path(m.file.iloc[0]).parent.as_posix()
    chk(f"file == '<folder>/<item>.jpg' ({k})", (m.file == folder + "/" + m["item"] + ".jpg").all(), int((m.file != folder + "/" + m["item"] + ".jpg").sum()), folder)
chk("licence identical across the three manifests", pd.concat([m.licence for m in MAN.values()]).nunique() == 1, 0, str(pd.concat([m.licence for m in MAN.values()]).unique()))
b1 = MAN["main"].merge(STAT[["id", "brightness"]], left_on="parent_pano_id", right_on="id", suffixes=("", "_stat"))
chk("brightness manifest == collection_status (main)", (b1.brightness == b1.brightness_stat).all() and len(b1) == 2999, int((b1.brightness != b1.brightness_stat).sum()))
b2 = MAN["extra"].merge(POOL[["id", "brightness"]], left_on="parent_pano_id", right_on="id", suffixes=("", "_pool"))
chk("brightness manifest == candidate pool (train_extra)", (b2.brightness == b2.brightness_pool).all() and len(b2) == 2000, int((b2.brightness != b2.brightness_pool).sum()))
nt = pd.concat([STAT[STAT.status == "night"].brightness, POOL[POOL.status == "night"].brightness])
okb = pd.concat([STAT[STAT.status == "ok"].brightness, POOL[POOL.status == "ok"].brightness])
NUM["night_filter"] = dict(night_max=int(nt.max()), n_night_at_90=int((nt == 90).sum()), n_night=len(nt), ok_min=int(okb.min()))
chk("night panos (status 'night') have brightness < 90, kept (ok) panos >= 90", (nt < 90).all() and (okb >= 90).all(), int((nt >= 90).sum()),
    f"night max {nt.max()} ({int((nt == 90).sum())} of {len(nt)} night panos have brightness exactly 90, i.e. filter is effectively <= 90); ok min {okb.min()}")
chk("highway: street_candidates == train_extra annotations == yaml (75 extra streets)",
    (ANN_X.drop_duplicates("street_id").set_index("street_id").highway == D[D.phase == "train_extra"].drop_duplicates("street_id").set_index("street_id").highway).all()
    and all(D[D.street_id == s["id"]].highway.iloc[0] == s["highway"] for s in YX), 0)
allm0 = pd.concat(list(MAN.values()))
# stamped date oddity
odd = D[(D.year == 2016)]
NUM["captured_2016"] = {"n": len(odd), "by_creator": odd.creator.value_counts().to_dict(), "by_phase": odd.phase.value_counts().to_dict(),
                        "distinct_dates": sorted(pd.to_datetime(odd.captured_at, format="ISO8601").dt.date.astype(str).unique())[:10],
                        "n_distinct_dates": int(pd.to_datetime(odd.captured_at, format="ISO8601").dt.date.nunique())}
chk("bearing wrap: travel_bearing == 360.0 rows (count, harmless 360 = 0)", True, int((allm0.travel_bearing == 360).sum()), "item " + str(list(allm0[allm0.travel_bearing == 360].item)))
chk("captured_at not a placeholder date (year 2016 / 2016-01-01 stamps) [odd, report only]", len(odd) == 0, len(odd),
    f"{len(odd)} crops stamped 2016, distinct dates {NUM['captured_2016']['n_distinct_dates']}, creators {odd.creator.value_counts().to_dict()}")
# 12. outliers by 1.5 IQR (per group; pooled by manifest rows, groups kept apart)
orow, extreme = [], []
for var in ["brightness", "dist_to_street_m"]:
    for g, d in GROUPS_P.items():
        x = d[var]
        q1, q3 = x.quantile(.25), x.quantile(.75)
        lo, hi = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
        o = d[(x < lo) | (x > hi)]
        orow.append(dict(variable=var, group=g, n=len(d), q1=q1, q3=q3, fence_lo=lo, fence_hi=hi, n_below=int((x < lo).sum()), n_above=int((x > hi).sum()),
                         share_outliers=len(o) / len(d), min=x.min(), max=x.max(), n_at_min=int((x == x.min()).sum()), n_at_max=int((x == x.max()).sum())))
        e = pd.concat([d.nsmallest(5, var), d.nlargest(5, var)]).drop_duplicates("item")
        e = e.assign(variable=var, group=g, value=e[var], is_outlier=((e[var] < lo) | (e[var] > hi)))
        extreme.append(e[["variable", "group", "item", "street_id", "split", "label", "value", "is_outlier", "creator", "captured_at", "parent_pano_id"]])
OUTL = pd.DataFrame(orow)
wcsv(OUTL, "outliers_iqr.csv")
wcsv(pd.concat(extreme), "outliers_extreme_rows.csv")
NUM["outliers_iqr"] = {f"{r.variable}|{r.group}": dict(n_below=r.n_below, n_above=r.n_above, fence_lo=r.fence_lo, fence_hi=r.fence_hi, min=r.min, max=r.max,
                                                          n_at_max=r.n_at_max, n_at_min=r.n_at_min) for r in OUTL.itertuples()}
allm = pd.concat(list(MAN.values()))
NUM["dist_to_street_m"] = dict(max=allm.dist_to_street_m.max(), n_at_max=int((allm.dist_to_street_m == allm.dist_to_street_m.max()).sum()), n_zero=int((allm.dist_to_street_m == 0).sum()),
                               note="max and count at max/0.0 as computed; no interpretation (cause of 0.0 / 20.0 not checked against docs)")
chk("outliers (1.5 IQR) in brightness / dist_to_street_m: counts only, nothing changed", True, int(OUTL.n_below.sum() + OUTL.n_above.sum()),
    "see outliers_iqr.csv; per-group counts include pooled rows main_all/extra_all (double counting)")
CHKD = pd.DataFrame(CHK)
wcsv(CHKD, "consistency_checks.csv")
NUM["checks"] = {"n_checks": len(CHKD), "n_fail": int((CHKD.result == "FAIL").sum()), "failed": CHKD[CHKD.result == "FAIL"][["check", "violations", "detail"]].to_dict("records")}

# ------------------------------------------------------------------ cross-check against the docs
print("cross-check with docs")
g_ = lambda g: tuple(int((GROUPS_P[g].label == k).sum()) for k in "01I")
tr = lambda d: (int(d.n0.sum()), int(d.n1.sum()), int(d.nI.sum()))
ex = []


def X(name, doc, mine, tol=0):
    ok = (abs(doc - mine) <= tol) if isinstance(doc, (int, float, np.floating, np.integer)) else tuple(doc) == tuple(mine)
    ex.append(dict(item=name, doc=str(doc), computed=str(mine if not isinstance(mine, float) else round(mine, 4)), status="khớp" if ok else "LỆCH"))


X("main phase 0/1/I", (1558, 188, 1253), g_("main_all"))
X("pilot 0/1/I", (73, 14, 63), g_("pilot"))
X("train_extra v2 0/1/I", (819, 577, 604), g_("extra_all"))
X("top_score blocked / n", (531, 1400), (int(GROUPS["extra_top_score"].blocked.sum()), len(GROUPS["extra_top_score"])))
X("random blocked / n", (46, 600), (int(GROUPS["extra_random"].blocked.sum()), len(GROUPS["extra_random"])))
X("main train 0/1/I", (939, 106, 794), g_("main_train"))
X("main val 0/1/I", (207, 35, 244), g_("main_val"))
X("main test 0/1/I", (412, 47, 215), g_("main_test"))
x_ = D[D.phase.isin(["main", "pilot"])]
X("main+pilot: 0 / 1 / I / usable", (1631, 202, 1316, 1833), (int((x_.label == "0").sum()), int(x_.blocked.sum()), int((x_.label == "I").sum()), int(x_.usable.sum())))
X("train main+pilot 0/1/I", (1012, 120, 857), tuple(int(((D.split == "train") & (D.phase != "train_extra") & (D.label == k)).sum()) for k in "01I"))
X("train all phases: usable / blocked", (2528, 697), (int(Dtr.usable.sum()), int(Dtr.blocked.sum())))
X("share of train blocked from train_extra (docs: 83%)", 0.83, round(577 / 697, 2), 0.005)
X("train_extra v1 0/1/I (labels_v1 via annotation table)", (810, 588, 602), tuple(int((ANN_X.label == k).sum()) for k in "01I"))
X("train_extra v1: top_score blocked / random blocked", (541, 47), (int(((ANN_X.stratum == "top_score") & (ANN_X.label == "1")).sum()), int(((ANN_X.stratum == "random") & (ANN_X.label == "1")).sum())))
X("blocked share top_score v2 (docs 0,379)", 0.379, 531 / 1400, 0.0005)
X("blocked share random v2 (docs 0,077)", 0.077, 46 / 600, 0.0005)
X("blocked share all train_extra v2 (docs 0,288; exact 577/2000 = 0.2885)", 0.288, 577 / 2000, 0.0006)
X("main annotations / annotators x 887", (4435, 5, 887), (len(ANN_M), ANN_M.annotator.nunique(), int(ANN_M.annotator.value_counts().min())))
X("train_extra: crops / streets", (2000, 75), (len(EXL), EXL.street_id.nunique()))
X("main: crops / streets", (2999, 17), (len(MAN["main"]), MAN["main"].street_id.nunique()))
X("pilot / main + pilot labelled", (150, 3149), (len(MAN["pilot"]), len(LAB)))
X("train_extra v1->v2 changes", 17, len(chg))
X("train_extra v1 obstacle tags (annotation count, docs: Xe máy 351, Hàng hóa 221, Khác 66, Bàn ghế 49, Rào chắn 38, Ô tô 11)", (351, 221, 66, 49, 38, 11),
  tuple(int(OB[(OB.group == "extra_all (nhãn v1)") & (OB.tag == t)].n_with_tag.iloc[0]) for t in ["Xe máy đậu", "Hàng hóa / quầy hàng", "Khác", "Bàn ghế quán", "Rào chắn / công trình", "Ô tô đậu"]))
X("train_extra v1 I reasons (docs: 463, 106, 21, 9)", (463, 106, 21, 9), tuple(int((ANN_X.reason == r).sum()) for r in ["Không thấy vỉa hè", "Bị che", "Ảnh mờ / tối / cháy sáng", "Lý do khác"]))
X("highway counts of train_extra crops, top_score (docs: tertiary 846, secondary 266, residential 151, primary 137)", (846, 266, 151, 137),
  tuple(int((GROUPS["extra_top_score"].highway == h).sum()) for h in ["tertiary", "secondary", "residential", "primary"]))
X("highway counts of train_extra crops, random (docs: 384, 108, 38, 70)", (384, 108, 38, 70), tuple(int((GROUPS["extra_random"].highway == h).sum()) for h in ["tertiary", "secondary", "residential", "primary"]))
X("top streets (docs: Hoàng Sa 157, Trường Sa#0 117; min 6 crops)", (157, 117, 6), (int((MAN["extra"].street_id == "Hoàng Sa").sum()), int((MAN["extra"].street_id == "Trường Sa#0").sum()), int(MAN["extra"].street_id.value_counts().min())))
X("train_extra top_score tier: max crops per street (docs: 101; cap 350)", 101, int(GROUPS["extra_top_score"].street_id.value_counts().max()))
X("score mean: top_score 0.80 / random 0.23 (docs)", (0.80, 0.23), (round(GROUPS["extra_top_score"].score.mean(), 2), round(GROUPS["extra_random"].score.mean(), 2)))
# per-annotator docs tables
docs_main = {"Hoc": (.69, .10, .21, 2.1), "Khai": (.52, .08, .39, 3.4), "Loan": (.54, .06, .40, 5.9), "Minh": (.45, .05, .50, 2.3), "Phuc": (.47, .06, .47, 7.5)}
for a, v in docs_main.items():
    r = AN[(AN.source == "main") & (AN.by == "all") & (AN.annotator == a)].iloc[0]
    X(f"main annotator {a}: share 0/1/I, median s (docs)", v, (round(r.share0, 2), round(r.share1, 2), round(r.shareI, 2), round(r.median_s, 1)), 0.0501)
docs_ex = {"Hoc": (.43, .15, 16, 108, 3.8), "Khai": (.31, .08, 10, 131, 3.9), "Phuc": (.28, .09, 11, 125, 3.1), "Minh": (.25, .08, 9, 116, 3.8), "Loan": (.19, .01, 1, 120, 6.8)}
for a, v in docs_ex.items():
    t = ANN_X[ANN_X.annotator == a]
    tr_ = t[t.stratum == "random"]
    X(f"train_extra annotator {a}: blocked/crop, blocked/crop random (k, n), median s (v1; docs)", v,
      (round((t.label == "1").mean(), 2), round((tr_.label == "1").mean(), 2), int((tr_.label == "1").sum()), len(tr_), round(t.seconds.median(), 1)), 0.0501)
XC = pd.DataFrame(ex)
wcsv(XC, "docs_crosscheck.csv")
NUM["docs_crosscheck"] = {"n": len(XC), "mismatches": XC[XC.status != "khớp"].to_dict("records")}

# ================================================================== figures
print("figures")
gl = lambda g: f"{GNAME[g]}\n(n={vn(len(GROUPS[g]))})"

# fig 1: stacked label counts per group
fig, ax = plt.subplots(figsize=(6.6, 3.3))
ypos = np.array([0, 1, 2, 3.5, 5, 6])[::-1]
xmax = LC[LC.group.isin(GORDER)].n.max()
for y, g in zip(ypos, GORDER):
    r = LC[LC.group == g].iloc[0]
    left = 0
    for k in "01I":
        v = r[f"n{k}"]
        ax.barh(y, v, left=left, color=LABCOL[k], height=0.62, edgecolor="white", linewidth=0.5)
        if v > 0.07 * xmax:
            ax.text(left + v / 2, y, vn(v), ha="center", va="center", color="white", fontsize=8, fontweight="bold")
        left += v
    ax.text(left + 0.012 * xmax, y, f"0: {vn(r.n0)}  ·  1: {vn(r.n1)}  ·  I: {vn(r.nI)}  (n = {vn(r.n)})", va="center", fontsize=7.5)
ax.set_yticks(ypos)
ax.set_yticklabels([GNAME[g] for g in GORDER])
ax.set_xlim(0, xmax * 1.62)
ax.set_xlabel("Số ảnh cắt")
ax.set_title("Số ảnh theo nhãn trong từng nhóm (các nhóm không gộp)")
ax.legend(handles=[Patch(color=LABCOL[k], label=LABNAME[k]) for k in "01I"], loc="center right", bbox_to_anchor=(1, 0.58), frameon=False)
savefig(fig, "tab_fig1_label_counts_by_group.pdf")

# fig 2: blocked share among usable (Wilson) and among all
fig, ax = plt.subplots(figsize=(6.6, 3.4))
for y, g in zip(ypos, GORDER):
    r = LC[LC.group == g].iloc[0]
    ax.errorbar(r.blocked_share_usable, y + 0.14, xerr=[[r.blocked_share_usable - r.bu_lo], [r.bu_hi - r.blocked_share_usable]], fmt="o", color=C1, capsize=3, ms=6)
    ax.errorbar(r.blocked_share_all, y - 0.14, xerr=[[r.blocked_share_all - r.ba_lo], [r.ba_hi - r.blocked_share_all]], fmt="s", mfc="white", color=C1, capsize=3, ms=5)
    ax.text(0.64, y + 0.14, f"{vn(r.n1)}/{vn(r.usable)} = {r.blocked_share_usable:.1%}", va="center", fontsize=7.5)
    ax.text(0.64, y - 0.14, f"{vn(r.n1)}/{vn(r.n)} = {r.blocked_share_all:.1%}", va="center", fontsize=7.5, color="#555")
ax.axvline(float(LC[LC.group == "main_all"].blocked_share_usable.iloc[0]), color="#999", ls=":", lw=1)
ax.text(float(LC[LC.group == "main_all"].blocked_share_usable.iloc[0]) + 0.006, ypos[-1] - 0.75, "đường chấm: main tự nhiên gộp 3 split", fontsize=7, color="#666", va="center")
ax.set_ylim(ypos[-1] - 1.0, ypos[0] + 0.6)
ax.set_yticks(ypos)
ax.set_yticklabels([GNAME[g] for g in GORDER])
ax.set_xlim(0, 0.95)
ax.set_xlabel("Tỉ lệ Bị chặn (khoảng Wilson 95%)")
ax.set_title("Tỉ lệ Bị chặn theo nhóm (pilot và train-extra chọn theo điểm, không tự nhiên)", pad=22)
ax.legend(handles=[Line2D([], [], marker="o", color=C1, ls="", label="trên ảnh dùng được (0/1)"), Line2D([], [], marker="s", mfc="white", color=C1, ls="", label="trên mọi ảnh (cả I)")],
          loc="lower left", frameon=False, bbox_to_anchor=(0, 1.0), ncol=2)
savefig(fig, "tab_fig2_blocked_share_wilson.pdf")

# fig 3a: label composition per main street, ordered by split
sm = ST[ST.group_set == "main"].copy()
sm["o"] = sm.split.map({"train": 0, "val": 1, "test": 2})
sm = sm.sort_values(["o", "n"], ascending=[True, False]).reset_index(drop=True)
fig, ax = plt.subplots(figsize=(6.6, 5.0))
y = np.arange(len(sm))[::-1]
for i, r in sm.iterrows():
    left = 0
    for k in "01I":
        v = r[f"share{k}"]
        ax.barh(y[i], v, left=left, color=LABCOL[k], height=0.72, edgecolor="white", linewidth=0.4)
        if v > 0.07:
            ax.text(left + v / 2, y[i], f"{int(r['n' + k])}", ha="center", va="center", color="white", fontsize=7)
        left += v
    ax.text(1.01, y[i], f"n={int(r.n)}  |  Bị chặn/dùng được = {int(r.n1)}/{int(r.usable)}", va="center", fontsize=7)
ax.set_yticks(y)
ax.set_yticklabels(sm.street_id)
ax.set_xlim(0, 1)
ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
ax.set_xlabel("Tỉ lệ nhãn trong đường (số ảnh ghi trong ô)")
for s_, c_ in [("train", "#EEE"), ("val", "#DDD"), ("test", "#CCC")]:
    idx = y[sm.split == s_]
    ax.annotate(s_, xy=(0, (idx.max() + idx.min()) / 2), xytext=(-0.34, (idx.max() + idx.min()) / 2), textcoords=("axes fraction", "data"), xycoords=("axes fraction", "data"),
                ha="center", va="center", fontsize=9, fontweight="bold", color="#555")
for s_ in ["val", "test"]:
    ax.axhline(y[sm.split == s_].max() + 0.5, color="#888", lw=0.8, ls="--")
ax.set_title("Thành phần nhãn của 17 đường main tự nhiên (không gồm 150 ảnh pilot)", loc="left")
ax.legend(handles=[Patch(color=LABCOL[k], label=LABNAME[k]) for k in "01I"], loc="upper center", bbox_to_anchor=(0.45, -0.1), ncol=3, frameon=False)
savefig(fig, "tab_fig3a_main_street_composition.pdf")

# fig 3b: train_extra streets: sorted dot plot of blocked share among usable
se = ST[ST.group_set == "extra_all"].sort_values("blocked_share_usable", ascending=True).reset_index(drop=True)
fig, ax = plt.subplots(figsize=(6.6, 10.6))
y = np.arange(len(se))
ax.errorbar(se.blocked_share_usable, y, xerr=[se.blocked_share_usable - se.bu_lo, se.bu_hi - se.blocked_share_usable], fmt="none", ecolor="#E4575655", elinewidth=1)
ax.scatter(se.blocked_share_usable, y, s=14 + 2.2 * np.sqrt(se.usable), color=C1, zorder=3, edgecolor="white", linewidth=0.4)
for yy, r in zip(y, se.itertuples()):
    ax.text(1.04, yy, f"{int(r.n1)}/{int(r.usable)}  ({r.highway[:4]}.)", va="center", fontsize=6.3)
ax.set_yticks(y)
ax.set_yticklabels(se.street_id, fontsize=6.3)
ax.set_ylim(-1, len(se))
ax.set_xlim(0, 1.0)
ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
ax.axvline(577 / 1396, color="#999", ls=":", lw=1)
ax.text(577 / 1396 + 0.01, -0.9, f"chung 577/1.396 = {577 / 1396:.1%}", fontsize=6.5, color="#666")
ax.set_xlabel("Tỉ lệ Bị chặn trên ảnh dùng được (Wilson 95%); chấm to = nhiều ảnh")
ax.text(1.04, len(se) - 0.2, "Bị chặn/dùng được (loại đường)", fontsize=6.3, va="bottom")
small = float(D[(D.phase == "train_extra")].highway.isin(["tertiary", "residential"]).mean())
ax.set_title(f"75 đường train-extra, gộp hai tầng ({small:.0%} ảnh từ đường tertiary/residential; chọn theo điểm nên lệch)", fontsize=8.5, pad=14)
savefig(fig, "tab_fig3b_extra_streets_blocked_share.pdf")

# fig 4: brightness and dist boxplots by group
fig, axs = plt.subplots(1, 2, figsize=(6.8, 3.6), sharey=True)
for ax, var, lab in zip(axs, ["brightness", "dist_to_street_m"], ["Độ sáng (xám trung bình nửa trên pano)", "Khoảng cách tới tim đường (m)"]):
    bp = ax.boxplot([GROUPS[g][var] for g in GORDER], vert=False, positions=ypos, widths=0.55, patch_artist=True, flierprops=dict(marker=".", ms=2, mfc="#777", mec="none"),
                    medianprops=dict(color="black"), whis=1.5)
    for b_, g in zip(bp["boxes"], GORDER):
        b_.set_facecolor(GCOL[g])
        b_.set_edgecolor("#444")
    ax.set_xlabel(lab)
    if var == "brightness":
        ax.axvline(90, color="#888", ls="--", lw=0.8)
        ax.text(90.5, ypos[0] + 0.55, "ngưỡng đêm 90", fontsize=7, color="#666")
axs[0].set_yticks(ypos)
axs[0].set_yticklabels([gl(g) for g in GORDER], fontsize=7)
fig.suptitle("Phân bố độ sáng và khoảng cách theo nhóm (hộp = Q1–Q3, râu = 1,5·IQR)", x=0.02, ha="left", fontsize=10)
fig.tight_layout()
savefig(fig, "tab_fig4_brightness_dist_boxplots.pdf")

fig, axs = plt.subplots(1, 2, figsize=(6.8, 3.0))
sets = [("main tự nhiên (3 split gộp)", D[D.phase == "main"], GCOL["main_train"]), ("pilot", GROUPS["pilot"], GCOL["pilot"]),
        ("train-extra top_score", GROUPS["extra_top_score"], GCOL["extra_top_score"]), ("train-extra random", GROUPS["extra_random"], GCOL["extra_random"])]
for ax, var, bins, lab in [(axs[0], "brightness", np.arange(90, 256, 6), "Độ sáng"), (axs[1], "dist_to_street_m", np.arange(0, 20.5, 1), "Khoảng cách tới tim đường (m)")]:
    for nm, d, c in sets:
        ax.hist(d[var], bins=bins, density=True, histtype="step", color=c, lw=1.6, label=nm)
    ax.set_xlabel(lab)
    ax.set_ylabel("Mật độ")
fig.legend(*axs[0].get_legend_handles_labels(), loc="lower center", ncol=4, frameon=False, fontsize=7.5, bbox_to_anchor=(0.5, -0.1))
fig.suptitle("Hình dạng phân bố độ sáng và khoảng cách (chuẩn hoá theo nhóm)", x=0.02, ha="left", fontsize=10)
fig.tight_layout()
savefig(fig, "tab_fig4b_brightness_dist_histograms.pdf")

# fig 5: year x creator, per phase; hour histogram
fig, axs = plt.subplots(1, 3, figsize=(6.8, 3.2), sharey=False)
creators = [c for c in CRE_COL if c in set(D.creator)]
for ax, (ph, ttl) in zip(axs, [("main", "main tự nhiên"), ("pilot", "pilot"), ("train_extra", "train-extra")]):
    ct = D[D.phase == ph].groupby(["year", "creator"]).size().unstack(fill_value=0).reindex(columns=creators, fill_value=0)
    bottom = np.zeros(len(ct))
    for c in creators:
        ax.bar(ct.index.astype(str), ct[c], bottom=bottom, color=CRE_COL[c], edgecolor="white", linewidth=0.4)
        bottom += ct[c].to_numpy()
    for xi, tot in enumerate(bottom):
        ax.text(xi, tot, vn(tot), ha="center", va="bottom", fontsize=7)
    ax.set_title(ttl, fontsize=9, pad=8)
    ax.margins(y=0.14)
    ax.set_xlabel("Năm chụp")
axs[0].set_ylabel("Số ảnh cắt")
fig.legend(handles=[Patch(color=CRE_COL[c], label=c) for c in creators], loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.12), fontsize=7.5)
fig.suptitle("Năm chụp theo nhà đóng góp (creator) Mapillary", x=0.02, ha="left", fontsize=10)
fig.tight_layout()
savefig(fig, "tab_fig5_year_creator.pdf")

fig, axs = plt.subplots(1, 3, figsize=(6.8, 2.9), sharey=False)
for ax, (ph, ttl) in zip(axs, [("main", "main tự nhiên"), ("pilot", "pilot"), ("train_extra", "train-extra")]):
    ct = D[D.phase == ph].groupby(["hour", "creator"]).size().unstack(fill_value=0).reindex(index=range(24), columns=creators, fill_value=0)
    bottom = np.zeros(24)
    for c in creators:
        ax.bar(range(24), ct[c], bottom=bottom, color=CRE_COL[c], width=0.85)
        bottom += ct[c].to_numpy()
    ax.set_title(ttl, fontsize=9)
    ax.set_xlabel("Giờ ghi (+07:00)")
    ax.set_xticks([0, 6, 12, 18, 23])
axs[0].set_ylabel("Số ảnh cắt")
fig.legend(handles=[Patch(color=CRE_COL[c], label=c) for c in creators], loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.16), fontsize=7.5)
fig.suptitle("Giờ ghi trên dấu thời gian (không đáng tin theo docs/collection_log.md; chỉ để minh chứng)", x=0.02, ha="left", fontsize=9.5)
fig.tight_layout()
savefig(fig, "tab_fig5b_stamped_hour_hist.pdf")

# fig 6: Spearman heatmaps (main_all, extra_all)
vlab = {"brightness": "độ sáng", "dist_to_street_m": "khoảng cách\ntới tim đường", "lat": "vĩ độ", "lon": "kinh độ", "year": "năm chụp", "travel_bearing": "hướng chạy xe",
        "score": "điểm bộ chọn"}
fig, axs = plt.subplots(1, 2, figsize=(8.4, 4.4), gridspec_kw=dict(width_ratios=[6, 7], wspace=0.95))
for ax, sub, ttl in [(axs[0], "main_all", "main tự nhiên (gộp 3 split, n=2.999)"), (axs[1], "extra_all", "train-extra (n=2.000)")]:
    m = SP[sub]
    im = ax.imshow(m.to_numpy(), cmap="PuOr_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(m)))
    ax.set_yticks(range(len(m)))
    ax.set_xticklabels([vlab[c] for c in m.columns], rotation=45, ha="right", fontsize=7)
    ax.set_yticklabels([vlab[c] for c in m.index], fontsize=7)
    for i in range(len(m)):
        for j in range(len(m)):
            v = m.iloc[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7, color="white" if abs(v) > 0.6 else "black")
    ax.set_title(ttl, fontsize=9)
    for s_ in ax.spines.values():
        s_.set_visible(False)
fig.colorbar(im, ax=axs, shrink=0.75, pad=0.03, label="Hệ số Spearman")
fig.suptitle("Tương quan hạng giữa các thuộc tính số của siêu dữ liệu", x=0.02, ha="left", fontsize=10)
savefig(fig, "tab_fig6_spearman_heatmap.pdf")

# fig 7: obstacle tags and I-reasons main vs extra
fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.3))
ax = axs[0]
yy = np.arange(len(TAGS))[::-1]
for off, g, c, nm in [(0.19, "main_all", GCOL["main_train"], "main tự nhiên"), (-0.19, "extra_all", GCOL["extra_top_score"], "train-extra")]:
    s = OB[(OB.group == g) & (OB.basis.str.startswith("item")) & OB.tag.isin(TAGS)].set_index("tag").reindex(TAGS)
    ax.barh(yy + off, s.share, height=0.36, color=c, label=f"{nm} (n={int(s.denominator.iloc[0])} ảnh Bị chặn)")
    for yv, r in zip(yy + off, s.itertuples()):
        ax.text(r.share + 0.01, yv, f"{r.share:.0%}", va="center", fontsize=7)
ax.set_yticks(yy)
ax.set_yticklabels(TAGS)
ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
ax.set_xlim(0, 0.95)
ax.set_xlabel("Tỉ lệ ảnh Bị chặn có thẻ (nhiều thẻ/ảnh)")
ax.set_title("Vật cản trên ảnh Bị chặn", fontsize=9)
ax.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.22))
ax = axs[1]
yy = np.arange(len(REASONS))[::-1]
for off, g, c, nm in [(0.19, "main_all", GCOL["main_train"], "main tự nhiên"), (-0.19, "extra_all", GCOL["extra_top_score"], "train-extra")]:
    s = RS[(RS.group == g) & RS.reason.isin(REASONS)].set_index("reason").reindex(REASONS)
    known = s.n.sum()
    ax.barh(yy + off, s.n / known, height=0.36, color=c, label=f"{nm}: {vn(known)}/{vn(s.n_I.iloc[0])} ảnh I có lý do")
    for yv, r in zip(yy + off, s.itertuples()):
        ax.text(r.n / known + 0.01, yv, f"{r.n / known:.0%}", va="center", fontsize=7)
ax.set_yticks(yy)
ax.set_yticklabels(["Không thấy\nvỉa hè", "Bị che", "Ảnh mờ / tối /\ncháy sáng", "Lý do khác"])
ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
ax.set_xlim(0, 0.95)
ax.set_xlabel("Tỉ lệ trong các ảnh I có ghi lý do")
ax.set_title("Lý do Không đủ thông tin", fontsize=9)
ax.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.22))
fig.tight_layout()
savefig(fig, "tab_fig7_obstacles_reasons.pdf")

# fig 8: per-annotator label shares
fig, axs = plt.subplots(1, 2, figsize=(7.0, 2.9), sharey=True)
for ax, src, ttl in [(axs[0], "main", "Main: mọi lượt gán (4.435 lượt)"), (axs[1], "train_extra", "Train-extra: nhãn v1 (2.000 lượt)")]:
    a = AN[(AN.source == src) & (AN.by == "all")].set_index("annotator").loc[list(ANN_VN)]
    yy = np.arange(len(a))[::-1]
    left = np.zeros(len(a))
    for k in "01I":
        v = a[f"share{k}"].to_numpy()
        ax.barh(yy, v, left=left, color=LABCOL[k], height=0.66, edgecolor="white", linewidth=0.4)
        for yv, l, vv in zip(yy, left, v):
            if vv > 0.06:
                ax.text(l + vv / 2, yv, f"{vv:.0%}", ha="center", va="center", color="white", fontsize=7.5)
        left += v
    for yv, r in zip(yy, a.itertuples()):
        ax.text(1.01, yv, f"n={int(r.n)}", va="center", fontsize=7)
    ax.set_yticks(yy)
    ax.set_yticklabels([ANN_VN[x] for x in a.index])
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_title(ttl, fontsize=9)
fig.legend(handles=[Patch(color=LABCOL[k], label=LABNAME[k]) for k in "01I"], loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.1))
fig.tight_layout()
savefig(fig, "tab_fig8_annotator_label_shares.pdf")

# fig 9: association effect sizes
subs_plot = [("main_train", GCOL["main_train"], "main train"), ("main_all", "#2B5C42", "main gộp 3 split"), ("extra_all", GCOL["extra_top_score"], "train-extra")]
vl2 = {**vlab, "bear_sin": "sin(hướng xe)", "bear_cos": "cos(hướng xe)"}
fig, axs = plt.subplots(1, 2, figsize=(7.0, 4.0), sharey=True)
varlist = ["brightness", "dist_to_street_m", "lat", "lon", "year", "bear_sin", "bear_cos", "score"]
for ax, tgt, ttl in [(axs[0], "blocked_vs_passable", "Bị chặn so với Còn lối đi"), (axs[1], "I_vs_usable", "Không đủ thông tin so với dùng được")]:
    yy = np.arange(len(varlist))[::-1]
    for off, (sub, c, nm) in zip([0.24, 0, -0.24], subs_plot):
        s = AUCT[(AUCT.subset == sub) & (AUCT.target == tgt)].set_index("variable").reindex(varlist)
        ok = s.auc_pos_higher.notna()
        ax.errorbar(s.auc_pos_higher[ok], (yy + off)[ok.to_numpy()], xerr=[(s.auc_pos_higher - s.auc_lo_cluster)[ok].clip(lower=0), (s.auc_hi_cluster - s.auc_pos_higher)[ok].clip(lower=0)], fmt="o", ms=4, color=c, capsize=2, lw=1, label=nm)
    ax.axvline(0.5, color="#888", lw=0.8)
    ax.set_yticks(yy)
    ax.set_yticklabels([vl2[v].replace("\n", " ") for v in varlist])
    ax.set_xlim(0.2, 0.8)
    ax.set_xlabel("AUC")
    ax.set_title(ttl, fontsize=9)
axs[0].legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(1.1, -0.22), ncol=3)
fig.suptitle("Siêu dữ liệu số phân biệt nhãn tới đâu (AUC 0,5 = không phân biệt; AUC của lớp dương; thanh = khoảng 95% bootstrap theo đường)", x=0.02, ha="left", fontsize=8.5)
fig.tight_layout()
savefig(fig, "tab_fig9a_assoc_auc.pdf")

fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.3), sharey=True)
cvars = ["street_id", "creator", "year", "highway", "month"]
for ax, tgt, ttl in [(axs[0], "blocked_vs_passable", "Bị chặn so với Còn lối đi"), (axs[1], "I_vs_usable", "Không đủ thông tin so với dùng được")]:
    yy = np.arange(len(cvars))[::-1]
    for off, (sub, c, nm) in zip([0.24, 0, -0.24], subs_plot):
        s = CRAMT[(CRAMT.subset == sub) & (CRAMT.target == tgt)].set_index("variable").reindex(cvars)
        ax.barh(yy + off, s.cramers_v_bc, height=0.22, color=c, label=nm)
        lo, hi = s.v_lo_cluster, s.v_hi_cluster
        ax.errorbar(s.cramers_v_bc, yy + off, xerr=[(s.cramers_v_bc - lo).fillna(0).clip(lower=0), (hi - s.cramers_v_bc).fillna(0).clip(lower=0)], fmt="none", ecolor="black", elinewidth=0.7, capsize=1.5)
    ax.set_yticks(yy)
    ax.set_yticklabels(["đường (street_id)", "nhà đóng góp", "năm chụp", "loại đường", "tháng chụp"])
    ax.set_xlabel("Cramér's V hiệu chỉnh lệch (bias-corrected)")
    ax.set_title(ttl, fontsize=9)
axs[0].legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(1.1, -0.2), ncol=3)
fig.suptitle("Siêu dữ liệu phân loại liên hệ với nhãn tới đâu (đường: không có thanh, vì là cụm)", x=0.02, ha="left", fontsize=9.5)
fig.tight_layout()
savefig(fig, "tab_fig9b_assoc_cramers_v.pdf")

# fig 10: train composition before/after adding train_extra
fig, ax = plt.subplots(figsize=(6.8, 3.0))
yy = np.arange(len(TC))[::-1]
mx_ = TC.usable.max()
for yv, r in zip(yy, TC.itertuples()):
    ax.barh(yv, r.n0, color=C0, height=0.62)
    ax.barh(yv, r.n1, left=r.n0, color=C1, height=0.62)
    ax.text(r.usable + 0.01 * mx_, yv, f"Bị chặn {vn(r.n1)}/{vn(r.usable)} = {r.blocked_share_usable:.1%}  [{r.bu_lo:.1%}; {r.bu_hi:.1%}]  ·  0:1 = {r.imbalance_0_to_1:.1f}", va="center", fontsize=6.8)
ax.set_yticks(yy)
ax.set_yticklabels([n.replace(" (", "\n(") for n in TC.group], fontsize=6.8)
ax.set_xlim(0, mx_ * 1.9)
ax.set_xlabel("Số ảnh dùng được (0 và 1) trong train")
ax.set_title(f"Thành phần train trước và sau khi thêm train-extra ({TC.share_blocked_from_extra.iloc[3]:.0%} ảnh Bị chặn của train đến từ train-extra)", fontsize=9)
ax.legend(handles=[Patch(color=C0, label=LABNAME["0"]), Patch(color=C1, label=LABNAME["1"])], loc="upper center", bbox_to_anchor=(0.45, -0.18), ncol=2, frameon=False)
fig.tight_layout()
savefig(fig, "tab_fig10_train_composition.pdf")

# fig 11: seconds per annotation (heavy tail)
fig, ax = plt.subplots(figsize=(6.6, 2.8))
bins = np.linspace(-0.4, 5, 55)
for nm, s, c in [("main (4.435 lượt)", ANN_M.seconds, GCOL["main_train"]), ("train-extra (2.000 lượt)", ANN_X.seconds, GCOL["extra_top_score"])]:
    ax.hist(np.log10(s), bins=bins, density=True, histtype="step", color=c, lw=1.6, label=f"{nm}: trung vị {s.median():.1f} s, tối đa {s.max():,.0f} s".replace(",", "."))
ax.set_xticks([0, 1, 2, 3, 4, 5])
ax.set_xticklabels(["1 s", "10 s", "100 s", "1.000 s", "10.000 s", "100.000 s"])
ax.set_xlabel("Thời gian gán một ảnh (thang log)")
ax.set_ylabel("Mật độ")
ax.set_title("Thời gian gán nhãn có đuôi rất dài (ảnh để mở): dùng trung vị, không dùng trung bình")
ax.legend(frameon=False, fontsize=7.5)
savefig(fig, "tab_fig11_seconds_heavy_tail.pdf")


# ------------------------------------------------------------------ json
def _j(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o)
    return str(o)


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    return o


NUM["meta"] = dict(script="src/eda/28_eda_tabular.py", seed=SEED, bootstrap_B=B, groups=GNAME,
                   note="main_all / extra_all are pooled rows (named as such); val/test are descriptive only")
(TAB / "tabular_numbers.json").write_text(json.dumps(clean(NUM), ensure_ascii=False, indent=1, default=_j), encoding="utf-8")
print("  json   tabular_numbers.json")
print(f"checks: {NUM['checks']['n_checks']} total, {NUM['checks']['n_fail']} FAIL; docs cross-check mismatches: {len(NUM['docs_crosscheck']['mismatches'])}")
