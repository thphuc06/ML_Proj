"""EDA (data report): duplicates, near-duplicates, split leakage and visual diversity of the 5,149 crops.
Sections: 1 exact duplicates (md5 of file bytes / of decoded pixels, parent_pano_id); 2 near-duplicates (own 64-bit
dHash and pHash, DINOv2 cosine, all pairs) with three reference populations (same position other day / same street other
position / other street) and pair counts per split combination; 3 cross-split leakage (nearest train-side neighbour of
every val/test crop + image sheets); 4 spatial leakage (metric distances between panos of different splits, shared
street / position / sequence, map); 5 diversity (within-group cosine, effective rank, t-SNE, label-free domain-classifier AUC).
Labels of val/test are used ONLY to colour the t-SNE panel (descriptive). No threshold is chosen with them; no file is
modified or removed. All numbers are written to duplicate_numbers.json.
Inputs : data/labels/main_labels_v1.csv, data/labels/train_extra_labels_v2.csv, data/manifest/{main_v1,pilot_v2,train_extra_v1}.csv,
         data/crops/<file> (640 px JPEG; ~670 val/test crops were rebuilt from the panos on 2026-11-14, see 27_rebuild_missing_crops.py)
Cache  : data/raw/embeddings/dinov2_b14_eda.npz (new file, DINOv2 ViT-B/14 CLS+mean-patch of all crops; existing caches untouched)
Outputs: docs/data_report/tables/dup_*.csv, duplicate_numbers.json; docs/data_report/figures/dup_*.pdf (plots) and dup_sheet_*.jpg
Run    : .venv\\Scripts\\python.exe src\\eda\\30_eda_duplicates.py [--preview DIR]   (DIR gets PNG copies of the PDFs)"""
import argparse
import datetime
import hashlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, enrich.py

import matplotlib
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from scipy.fft import dctn

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import DATA, LAT0, ROOT, to_xy

OUT_T = ROOT / "docs" / "data_report" / "tables"
OUT_F = ROOT / "docs" / "data_report" / "figures"
OUT_T.mkdir(parents=True, exist_ok=True)
OUT_F.mkdir(parents=True, exist_ok=True)
ap = argparse.ArgumentParser()
ap.add_argument("--preview", default=None)
ARGS = ap.parse_args()
PREVIEW = Path(ARGS.preview) if ARGS.preview else None
if PREVIEW:
    PREVIEW.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8,
                     "legend.fontsize": 7.5, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "pdf.fonttype": 42,
                     "axes.spines.top": False, "axes.spines.right": False})
GROUPS = ["main_train", "pilot", "te_top_score", "te_random", "val", "test"]
GCOL = {"main_train": "#4C78A8", "pilot": "#F58518", "te_top_score": "#B279A2", "te_random": "#54A24B", "val": "#E45756", "test": "#222222"}
GNAME = {"main_train": "main (train)", "pilot": "pilot (train)", "te_top_score": "train_extra top_score",
         "te_random": "train_extra random", "val": "val", "test": "test"}
LCOL = {"0": "#4C78A8", "1": "#E45756", "I": "#9D9D9D"}
N = {}  # headline numbers -> duplicate_numbers.json
CAP = "© Mapillary contributors, CC BY-SA 4.0"


def log(*a):
    print(*a, flush=True)


def savefig(fig, name):
    fig.savefig(OUT_F / f"{name}.pdf", bbox_inches="tight")
    if PREVIEW:
        fig.savefig(PREVIEW / f"{name}.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, float) and np.isnan(o):
        return None
    return o


# ------------------------------------------------------------------ load
lab = pd.concat([pd.read_csv(DATA / "labels" / f, encoding="utf-8-sig", dtype=str) for f in ("main_labels_v1.csv", "train_extra_labels_v2.csv")], ignore_index=True)
man = pd.concat([pd.read_csv(DATA / "manifest" / f, encoding="utf-8-sig", dtype=str) for f in ("main_v1.csv", "pilot_v2.csv", "train_extra_v1.csv")], ignore_index=True)
keep = ["item", "parent_pano_id", "position_group", "lat", "lon", "captured_at", "creator", "sequence", "travel_bearing", "yaw", "street_id", "split"]
df = lab.merge(man[keep], on="item", how="left", suffixes=("", "_man"))
N["manifest_mismatch_street_or_split"] = int(((df.street_id != df.street_id_man) | (df.split != df.split_man)).sum())
df = df.drop(columns=["street_id_man", "split_man", "source", "reason"])
df["lat"], df["lon"] = df.lat.astype(float), df.lon.astype(float)
df["group"] = np.where(df.phase == "main", np.where(df.split == "train", "main_train", df.split),
                       np.where(df.phase == "pilot", "pilot", "te_" + df.stratum.fillna("")))
assert set(df.group) == set(GROUPS), set(df.group)
df["day"] = df.captured_at.str[:10]
df["path"] = [DATA / "crops" / f for f in df.file]
df["exists"] = [p.exists() for p in df.path]
miss = df[~df.exists]
N["n_rows"] = len(df)
N["missing_crops"] = {"n": len(miss), "items": miss.item.tolist()}
if len(miss):
    log(f"WARNING {len(miss)} crops missing, dropped: {miss.item.tolist()}")
df = df[df.exists].reset_index(drop=True)
n = len(df)
N["group_sizes"] = df.group.value_counts().reindex(GROUPS).to_dict()
N["split_sizes_main"] = df[df.phase == "main"].split.value_counts().to_dict()
N["n_crops_used"] = n
log("groups", N["group_sizes"])
g = df.group.map({k: i for i, k in enumerate(GROUPS)}).to_numpy()
is_train = df.group.isin(["main_train", "pilot", "te_top_score", "te_random"]).to_numpy()
is_vt = df.group.isin(["val", "test"]).to_numpy()
street = pd.factorize(df.street_id)[0]
pos_has = df.position_group.notna().to_numpy()
pos = np.where(pos_has, pd.factorize(df.position_group)[0], -1)
day = pd.factorize(df.day)[0]
x, y = to_xy(df.lon.to_numpy(), df.lat.to_numpy())
xy = np.c_[x, y].astype(np.float32)
D = np.sqrt(((xy[:, None, :] - xy[None, :, :]) ** 2).sum(-1)).astype(np.float32)  # metres between panos
rebuilt = np.array([datetime.date.fromtimestamp(Path(p).stat().st_mtime) >= datetime.date(2026, 11, 14) for p in df.path])  # file mtime (local date): rebuilt by 27_rebuild_missing_crops.py
df["rebuilt_2026_11_14"] = rebuilt
N["crops_with_mtime_2026_11_14"] = df[rebuilt].group.value_counts().reindex(GROUPS, fill_value=0).to_dict()
tag = {"main_train": "main-tr", "pilot": "pilot", "te_top_score": "te-top", "te_random": "te-rnd", "val": "val", "test": "test"}

# ------------------------------------------------------------------ 1. exact duplicates + hashes
log("hashing images ...")
md5f, md5p, dh, ph = [], [], [], []
for p in df.path:
    raw = Path(p).read_bytes()
    md5f.append(hashlib.md5(raw).hexdigest())
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    md5p.append(hashlib.md5(np.asarray(im).tobytes()).hexdigest())
    gr = im.convert("L")
    a = np.asarray(gr.resize((9, 8), Image.Resampling.LANCZOS), dtype=np.float32)
    dh.append((a[:, 1:] > a[:, :-1]).ravel())  # 64-bit dHash: horizontal gradient sign on a 9x8 grey thumbnail
    b = dctn(np.asarray(gr.resize((32, 32), Image.Resampling.LANCZOS), dtype=np.float32), type=2, axes=(0, 1))[:8, :8]
    ph.append((b > np.median(b)).ravel())  # 64-bit pHash: low-frequency 8x8 DCT block vs its median
df["md5_file"], df["md5_pixels"] = md5f, md5p
dh, ph = np.array(dh), np.array(ph)
df["dhash"] = [f"{int(''.join('1' if v else '0' for v in r), 2):016x}" for r in dh]
df["phash"] = [f"{int(''.join('1' if v else '0' for v in r), 2):016x}" for r in ph]


def dup_groups(col):
    d = df[df.duplicated(col, keep=False)].sort_values(col)
    return d[list(dict.fromkeys(["item", "group", "street_id", "split", "parent_pano_id", col]))]


ex = {}
for col in ("md5_file", "md5_pixels", "parent_pano_id"):
    d = dup_groups(col)
    ex[col] = {"n_rows_in_dup_groups": len(d), "n_groups": int(d[col].nunique()), "items": d.item.tolist()}
    d.to_csv(OUT_T / f"dup_exact_{col}.csv", index=False, encoding="utf-8-sig")
df["latlon"] = df.lat.round(8).astype(str) + "," + df.lon.round(8).astype(str)
d = dup_groups("latlon")
ex["identical_lat_lon_different_pano"] = {"n_rows": len(d), "items": d.item.tolist()}
d.to_csv(OUT_T / "dup_exact_latlon.csv", index=False, encoding="utf-8-sig")
N["exact"] = ex
# position_group shared by >1 pano: how many panos per position, how many days, across phases / splits
pg = df[pos_has].groupby("position_group").agg(n=("item", "size"), n_days=("day", "nunique"), n_phase=("phase", "nunique"),
                                              n_split=("split", "nunique"), n_group=("group", "nunique"))
N["position_group"] = {"n_positions": len(pg), "panos_per_position": pg.n.value_counts().sort_index().to_dict(),
                       "positions_with_2_panos_same_day": int(((pg.n == 2) & (pg.n_days == 1)).sum()),
                       "positions_shared_across_phase": int((pg.n_phase > 1).sum()),
                       "positions_shared_across_split": int((pg.n_split > 1).sum()),
                       "positions_shared_across_group": int((pg.n_group > 1).sum()),
                       "pilot_has_no_position_group": int((~pos_has).sum())}
pg.reset_index().to_csv(OUT_T / "dup_position_groups.csv", index=False, encoding="utf-8-sig")
pd.DataFrame({"group": GROUPS, "n_crops": [N["group_sizes"][k] for k in GROUPS]}).to_csv(OUT_T / "dup_group_sizes.csv", index=False)

# ------------------------------------------------------------------ 2. all-pairs metrics
TABLE = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def hamming(bits):
    pk = np.packbits(bits, axis=1)
    H = np.empty((n, n), dtype=np.uint8)
    for s in range(0, n, 128):
        H[s:s + 128] = TABLE[pk[s:s + 128, None, :] ^ pk[None, :, :]].sum(-1)
    return H


log("hamming matrices ...")
HD, HP = hamming(dh), hamming(ph)
emb_cache = DATA / "raw" / "embeddings"
from enrich import cached_embed  # noqa: E402

log("embeddings (cache dinov2_b14_eda) ...")
X = cached_embed("dinov2_b14", df.item.tolist(), [str(p) for p in df.path], log=log, cache="_eda")
CS = (X @ X.T).astype(np.float32)
N["embedding"] = {"model": "facebook/dinov2-base, CLS + mean patch, L2-normalised", "dim": int(X.shape[1])}
tri = np.triu(np.ones((n, n), dtype=bool), 1)
same_street = street[:, None] == street[None, :]
both_pos = (pos[:, None] >= 0) & (pos[None, :] >= 0)
same_pos = both_pos & (pos[:, None] == pos[None, :])
diff_day = day[:, None] != day[None, :]
same_phase = (df.phase.to_numpy()[:, None] == df.phase.to_numpy()[None, :])
is_main_ph, is_te_ph = (df.phase == "main").to_numpy(), (df.phase == "train_extra").to_numpy()
POPS = {
    "A_same_position_other_day": tri & same_pos & diff_day,
    "A_main": tri & same_pos & diff_day & is_main_ph[:, None] & is_main_ph[None, :],
    "A_train_extra": tri & same_pos & diff_day & is_te_ph[:, None] & is_te_ph[None, :],
    "B_same_street_other_position": tri & same_street & both_pos & ~same_pos,
    "B_near_same_street_other_position_lt30m": tri & same_street & both_pos & ~same_pos & (D < 30),
    "B_pilot_same_street_position_unknown": tri & same_street & ~both_pos,
    "C_other_street": tri & ~same_street,
}
N["pop_sizes"] = {k: int(m.sum()) for k, m in POPS.items()}
N["same_position_same_day_pairs"] = int((tri & same_pos & ~diff_day).sum())
QS = [0, 0.001, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 0.999, 1]
rows = []
for pn, m in POPS.items():
    for mn, M_ in (("cosine", CS), ("dhash", HD), ("phash", HP)):
        v = M_[m].astype(np.float64)
        rows.append({"population": pn, "metric": mn, "n_pairs": len(v), **{f"q{q}": (np.quantile(v, q) if len(v) else np.nan) for q in QS}, "mean": v.mean() if len(v) else np.nan})
pd.DataFrame(rows).to_csv(OUT_T / "dup_population_quantiles.csv", index=False, encoding="utf-8-sig")

THR = {"dhash": [0, 2, 4, 6, 8, 10, 12], "phash": [0, 2, 4, 6, 8, 10, 12], "cosine": [0.98, 0.95, 0.90, 0.85, 0.80, 0.75, 0.70]}
MAT = {"cosine": CS, "dhash": HD, "phash": HP}


def hit(mn, t):
    return (MAT[mn] >= t) if mn == "cosine" else (MAT[mn] <= t)


rows = []
for pn, m in POPS.items():
    tot = int(m.sum())
    for mn in MAT:
        for t in THR[mn]:
            c = int((m & hit(mn, t)).sum())
            rows.append({"population": pn, "metric": mn, "threshold": t, "n_pairs_pop": tot, "n_pairs_hit": c, "fraction": c / tot if tot else np.nan})
popthr = pd.DataFrame(rows)
popthr.to_csv(OUT_T / "dup_population_thresholds.csv", index=False, encoding="utf-8-sig")

# pair counts per group combination
combos = [(a, b) for a in range(6) for b in range(a, 6)]
size = np.bincount(g, minlength=6)
den = {(a, b): (size[a] * (size[a] - 1) // 2 if a == b else size[a] * size[b]) for a, b in combos}
GRP_COMBO_THR = {"dhash": [0, 4, 6, 8, 10], "phash": [0, 4, 6, 8, 10], "cosine": [0.95, 0.90, 0.85]}
cnt = {}
for mn, ts in GRP_COMBO_THR.items():
    for t in ts:
        ii, jj = np.nonzero(tri & hit(mn, t))
        a, b = np.minimum(g[ii], g[jj]), np.maximum(g[ii], g[jj])
        k = np.bincount(a * 6 + b, minlength=36)
        for (u, v) in combos:
            cnt[(mn, t, u, v)] = int(k[u * 6 + v])
rows = []
for (u, v) in combos:
    r = {"group_a": GROUPS[u], "group_b": GROUPS[v], "n_pairs": int(den[(u, v)])}
    for mn, ts in GRP_COMBO_THR.items():
        for t in ts:
            r[f"{mn}{'>=' if mn == 'cosine' else '<='}{t}"] = cnt[(mn, t, u, v)]
    rows.append(r)
pd.DataFrame(rows).to_csv(OUT_T / "dup_pair_counts_by_group_pair.csv", index=False, encoding="utf-8-sig")
gi = {k: i for i, k in enumerate(GROUPS)}


def combo(a, b):
    return (min(gi[a], gi[b]), max(gi[a], gi[b]))


TR = ["main_train", "pilot", "te_top_score", "te_random"]
AGG = {
    "within train-side: main-main": [combo("main_train", "main_train")],
    "within train-side: main-pilot": [combo("main_train", "pilot")],
    "within train-side: main-train_extra": [combo("main_train", a) for a in ("te_top_score", "te_random")],
    "within train-side: pilot-pilot": [combo("pilot", "pilot")],
    "within train-side: pilot-train_extra": [combo("pilot", a) for a in ("te_top_score", "te_random")],
    "within train-side: train_extra-train_extra": [combo(a, b) for a in ("te_top_score", "te_random") for b in ("te_top_score", "te_random") if a <= b],
    "within train-side: ALL": [combo(a, b) for a in TR for b in TR if gi[a] <= gi[b]],
    "train<->val: main_train": [combo("main_train", "val")],
    "train<->val: pilot": [combo("pilot", "val")],
    "train<->val: train_extra": [combo(a, "val") for a in ("te_top_score", "te_random")],
    "train<->val: ALL": [combo(a, "val") for a in TR],
    "train<->test: main_train": [combo("main_train", "test")],
    "train<->test: pilot": [combo("pilot", "test")],
    "train<->test: train_extra": [combo(a, "test") for a in ("te_top_score", "te_random")],
    "train<->test: ALL": [combo(a, "test") for a in TR],
    "val<->test": [combo("val", "test")],
    "val<->val": [combo("val", "val")],
    "test<->test": [combo("test", "test")],
    "train_extra<->val/test": [combo(a, b) for a in ("te_top_score", "te_random") for b in ("val", "test")],
}
rows = []
for name, cs_ in AGG.items():
    r = {"pair_class": name, "n_pairs": int(sum(den[c] for c in cs_))}
    for mn, ts in GRP_COMBO_THR.items():
        for t in ts:
            r[f"{mn}{'>=' if mn == 'cosine' else '<='}{t}"] = int(sum(cnt[(mn, t, *c)] for c in cs_))
    rows.append(r)
AGGT = pd.DataFrame(rows)
AGGT.to_csv(OUT_T / "dup_pair_counts_aggregated.csv", index=False, encoding="utf-8-sig")
N["pair_counts_aggregated"] = AGGT.set_index("pair_class").to_dict("index")

# figure: distributions of the three reference populations
fig, ax = plt.subplots(2, 2, figsize=(6.6, 5.6))
PC = {"A_same_position_other_day": ("#E45756", "Cùng vị trí, khác ngày"), "B_same_street_other_position": ("#4C78A8", "Cùng đường, khác vị trí"),
      "C_other_street": ("#7F7F7F", "Khác đường")}
bins_c = np.linspace(-0.05, 1.0, 85)
for pn, (c, lbl) in PC.items():
    m = POPS[pn]
    ax[0, 0].hist(CS[m], bins=bins_c, density=True, histtype="step", color=c, lw=1.2, label=lbl + " (n=" + f"{m.sum():,}".replace(",", ".") + ")")
    ax[0, 1].hist(HD[m], bins=np.arange(-0.5, 41.5), density=True, histtype="step", color=c, lw=1.2)
    ts = np.linspace(0, 1, 201)
    v = np.sort(CS[m])
    ax[1, 0].plot(ts, 1 - np.searchsorted(v, ts, side="left") / len(v) + 1e-9, color=c, lw=1.2)
    v = np.sort(HD[m])
    t2 = np.arange(0, 41)
    ax[1, 1].plot(t2, np.searchsorted(v, t2, side="right") / len(v) + 1e-9, color=c, lw=1.2, drawstyle="steps-post")
ax[0, 0].set_xlabel("Độ tương đồng cosine (DINOv2)"), ax[0, 0].set_ylabel("Mật độ")
ax[0, 1].set_xlabel("Khoảng cách Hamming dHash (64 bit)"), ax[0, 1].set_ylabel("Mật độ")
ax[1, 0].set_xlabel("Ngưỡng cosine t"), ax[1, 0].set_ylabel("Tỉ lệ cặp có cosine ≥ t"), ax[1, 0].set_yscale("log"), ax[1, 0].set_ylim(1e-6, 1.5)
ax[1, 1].set_xlabel("Ngưỡng dHash t"), ax[1, 1].set_ylabel("Tỉ lệ cặp có dHash ≤ t"), ax[1, 1].set_yscale("log"), ax[1, 1].set_ylim(1e-6, 1.5)
for t in (0.95, 0.90, 0.85):
    ax[1, 0].axvline(t, color="k", lw=0.5, ls=":")
for t in (4, 6, 8, 10):
    ax[1, 1].axvline(t, color="k", lw=0.5, ls=":")
fig.legend(*ax[0, 0].get_legend_handles_labels(), loc="upper center", ncol=3, frameon=False, fontsize=6.8, bbox_to_anchor=(0.5, 1.0), handlelength=1.2, columnspacing=1.0)
fig.tight_layout(rect=(0, 0, 1, 0.96))
savefig(fig, "dup_distance_distributions")

# ------------------------------------------------------------------ sheets
FONT = ImageFont.truetype(str(Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf"), 11)


def sheet(pairs, name, ncols, tile, header=None):
    """pairs: list of (i, j, text_left, text_right, text_centre). Long side <= 2000 px, JPEG q85, licence caption at bottom."""
    nrows = -(-len(pairs) // ncols)
    gap, pad, cap_h, foot = 4, 10, 46, 28
    cw = 2 * tile + gap + pad
    W, Hh = ncols * cw + pad, nrows * (tile + cap_h + pad) + pad + foot
    assert max(W, Hh) <= 2000, (W, Hh)
    cv = Image.new("RGB", (W, Hh), "white")
    d = ImageDraw.Draw(cv)
    for k, (i, j, tl, tr, tc) in enumerate(pairs):
        r, c = divmod(k, ncols)
        x0, y0 = pad + c * cw, pad + r * (tile + cap_h + pad)
        for off, idx, t in ((0, i, tl), (tile + gap, j, tr)):
            cv.paste(Image.open(df.path[idx]).convert("RGB").resize((tile, tile), Image.Resampling.LANCZOS), (x0 + off, y0))
            for li, line in enumerate(t.split("\n")):
                while d.textlength(line, font=FONT) > tile and len(line) > 3:
                    line = line[:-2] + "…"
                d.text((x0 + off, y0 + tile + 2 + 14 * li), line, fill="black", font=FONT)
        d.text((x0, y0 + tile + 2 + 28), tc, fill=(160, 0, 0), font=FONT)
    d.text((pad, Hh - foot + 6), CAP, fill=(60, 60, 60), font=FONT)
    cv.save(OUT_F / f"{name}.jpg", quality=85)
    log(f"sheet {name}.jpg {cv.size}")


def desc(i):
    return f"{df.item[i]} {tag[df.group[i]]} | {df.street_id[i]}"


def tcap(k, i, j):
    return f"#{k + 1}  cos {CS[i, j]:.3f} | dHash {HD[i, j]} | pHash {HP[i, j]} | {D[i, j]:.0f} m" + ("  [cùng vị trí]" if same_pos[i, j] else "")


def top_pairs(sel_i, sel_j, M_, largest, k=20, exclude=None):
    """k extreme pairs between index sets (or within one set if sel_j is None); returns list of (i, j)."""
    if sel_j is None:
        S = M_[np.ix_(sel_i, sel_i)].astype(np.float64)
        S = np.where(np.triu(np.ones_like(S, dtype=bool), 1), S, -np.inf if largest else np.inf)
        if exclude is not None:
            S = np.where(exclude[np.ix_(sel_i, sel_i)], -np.inf if largest else np.inf, S)
    else:
        S = M_[np.ix_(sel_i, sel_j)].astype(np.float64)
    flat = S.ravel() if largest else -S.ravel()
    idx = np.argsort(-flat, kind="stable")[:k]
    out = []
    for f in idx:
        a, b = divmod(int(f), S.shape[1])
        out.append((sel_i[a], (sel_i if sel_j is None else sel_j)[b]))
    return out


vt_i, tr_i = np.where(is_vt)[0], np.where(is_train)[0]
cross_cos = top_pairs(vt_i, tr_i, CS, True)
# dHash: ties are broken by larger cosine (rank by hamming then -cosine)
score = HD[np.ix_(vt_i, tr_i)].astype(np.float64) - CS[np.ix_(vt_i, tr_i)] * 0.5
cross_dh = [(vt_i[a], tr_i[b]) for a, b in (divmod(int(f), len(tr_i)) for f in np.argsort(score.ravel(), kind="stable")[:20])]
trr = tr_i
within_all = top_pairs(trr, None, CS, True)


def mk(pl):
    return [(i, j, desc(i), desc(j), tcap(k, i, j)) for k, (i, j) in enumerate(pl)]


sheet(mk(cross_cos), "dup_sheet_cross_split_top20_cosine", 4, 240)
sheet(mk(cross_cos[:6]), "dup_sheet_cross_split_top6_cosine_zoom", 2, 490)
sheet(mk(cross_dh), "dup_sheet_cross_split_top20_dhash", 4, 240)
sheet(mk(within_all), "dup_sheet_within_train_top20_cosine", 4, 240)

rng_s = np.random.default_rng(0)
# calibration sheets (what the numbers look like): known same-position/other-day pairs, and a random sample of cross-split pairs in [0.85, 0.90)
ia, ja = np.nonzero(POPS["A_same_position_other_day"])
oa = np.argsort(-CS[ia, ja], kind="stable")[:20]
sheet(mk([(ia[o], ja[o]) for o in oa]), "dup_sheet_same_position_other_day_top20_cosine", 4, 240)
sel = (CS >= 0.85) & (CS < 0.90) & (is_vt[:, None] & is_train[None, :])
ib, jb = np.nonzero(sel)
N["cross_split_pairs_cos_0.85_0.90"] = int(len(ib))
ob = np.sort(rng_s.choice(len(ib), min(20, len(ib)), replace=False))
sheet(mk([(ib[o], jb[o]) for o in ob]), "dup_sheet_cross_split_cos_0.85_0.90_random20", 4, 240)


def pair_rows(pl):
    return [{"rank": k + 1, "item_a": df.item[i], "group_a": df.group[i], "street_a": df.street_id[i], "pano_a": df.parent_pano_id[i],
             "item_b": df.item[j], "group_b": df.group[j], "street_b": df.street_id[j], "pano_b": df.parent_pano_id[j],
             "cosine": float(CS[i, j]), "dhash": int(HD[i, j]), "phash": int(HP[i, j]), "dist_m": float(D[i, j]),
             "same_position_group": bool(same_pos[i, j]), "same_sequence": bool(df.sequence[i] == df.sequence[j])} for k, (i, j) in enumerate(pl)]


for nm, pl in (("cross_split_top20_cosine", cross_cos), ("cross_split_top20_dhash", cross_dh), ("within_train_top20_cosine", within_all)):
    pd.DataFrame(pair_rows(pl)).to_csv(OUT_T / f"dup_pairs_{nm}.csv", index=False, encoding="utf-8-sig")

# ------------------------------------------------------------------ 3. nearest train-side neighbour of val/test crops
Sc = CS[np.ix_(vt_i, tr_i)]
nn_c = Sc.argmax(1)
Sh = HD[np.ix_(vt_i, tr_i)].astype(np.int32) * 10 - (Sc * 5).astype(np.float64)  # lexicographic-ish: hamming first, cosine tie-break
nn_h = Sh.argmin(1)
Sp = HP[np.ix_(vt_i, tr_i)]
nn = pd.DataFrame({
    "item": df.item[vt_i].values, "split": df.split[vt_i].values, "street_id": df.street_id[vt_i].values,
    "nn_cos_item": df.item[tr_i[nn_c]].values, "nn_cos_group": df.group[tr_i[nn_c]].values, "nn_cos_street": df.street_id[tr_i[nn_c]].values,
    "nn_cos": Sc.max(1), "nn_cos_dhash": HD[vt_i, tr_i[nn_c]], "nn_cos_dist_m": D[vt_i, tr_i[nn_c]],
    "nn_dhash_item": df.item[tr_i[nn_h]].values, "nn_dhash_group": df.group[tr_i[nn_h]].values, "nn_dhash": HD[vt_i, tr_i[nn_h]],
    "nn_dhash_cos": CS[vt_i, tr_i[nn_h]], "nn_dhash_dist_m": D[vt_i, tr_i[nn_h]], "min_phash": Sp.min(1),
    "min_dist_m_to_train_side": D[np.ix_(vt_i, tr_i)].min(1)})
nn.to_csv(OUT_T / "dup_nn_val_test_to_train_side.csv", index=False, encoding="utf-8-sig")
# reference: nearest OTHER-street train-side neighbour of main-train crops (what 'different street' looks like inside train)
mt_i = np.where(df.group == "main_train")[0]
R = CS[np.ix_(mt_i, tr_i)].copy()
R[street[mt_i][:, None] == street[tr_i][None, :]] = -np.inf
ref_nn = R.max(1)
ref_nn_h = np.where(street[mt_i][:, None] == street[tr_i][None, :], 99, HD[np.ix_(mt_i, tr_i)]).min(1)
rows = []
for nm, vals, vals_h in (("val", nn.nn_cos[nn.split == "val"].values, nn.nn_dhash[nn.split == "val"].values),
                         ("test", nn.nn_cos[nn.split == "test"].values, nn.nn_dhash[nn.split == "test"].values),
                         ("ref: main_train -> other-street train-side", ref_nn, ref_nn_h)):
    r = {"set": nm, "n": len(vals)}
    r.update({f"cos_q{q}": float(np.quantile(vals, q)) for q in (0, 0.25, 0.5, 0.75, 0.95, 0.99, 1)})
    r.update({f"cos>={t}": int((vals >= t).sum()) for t in (0.95, 0.90, 0.85)})
    r.update({f"dhash_q{q}": float(np.quantile(vals_h, q)) for q in (0, 0.01, 0.05, 0.5)})
    r.update({f"dhash<={t}": int((vals_h <= t).sum()) for t in (4, 6, 8, 10)})
    rows.append(r)
nns = pd.DataFrame(rows)
nns.to_csv(OUT_T / "dup_nn_summary.csv", index=False, encoding="utf-8-sig")
N["nn_val_test_to_train_side"] = nns.set_index("set").to_dict("index")
N["nn_cos_source_group_counts"] = nn.groupby(["split", "nn_cos_group"]).size().to_dict()
N["max_cross_split_cosine"] = {"cosine": float(CS[np.ix_(vt_i, tr_i)].max()), "pair": pair_rows(cross_cos[:1])[0]}
N["min_cross_split_dhash"] = int(HD[np.ix_(vt_i, tr_i)].min())
N["min_cross_split_phash"] = int(HP[np.ix_(vt_i, tr_i)].min())
fig, ax = plt.subplots(1, 2, figsize=(6.6, 2.9))
for nm, vv, c in (("val", nn.nn_cos[nn.split == "val"], "#E45756"), ("test", nn.nn_cos[nn.split == "test"], "#222222")):
    ax[0].hist(vv, bins=np.linspace(0.3, 1, 71), density=True, histtype="step", color=c, lw=1.3, label=f"{nm} → train-side (n={len(vv)})")
ax[0].hist(ref_nn, bins=np.linspace(0.3, 1, 71), density=True, histtype="step", color="#4C78A8", lw=1.3, ls="--", label=f"main-train → đường khác (n={len(ref_nn)})")
for nm, vv, c in (("val", nn.nn_dhash[nn.split == "val"], "#E45756"), ("test", nn.nn_dhash[nn.split == "test"], "#222222")):
    ax[1].hist(vv, bins=np.arange(-0.5, 36.5), density=True, histtype="step", color=c, lw=1.3)
ax[1].hist(ref_nn_h, bins=np.arange(-0.5, 36.5), density=True, histtype="step", color="#4C78A8", lw=1.3, ls="--")
ax[0].set_xlabel("Cosine tới láng giềng gần nhất (train ∪ pilot ∪ train_extra)"), ax[0].set_ylabel("Mật độ")
ax[1].set_xlabel("dHash nhỏ nhất tới ảnh phía train"), ax[1].set_ylabel("Mật độ")
fig.legend(*ax[0].get_legend_handles_labels(), loc="upper center", ncol=3, frameon=False, fontsize=6.8, bbox_to_anchor=(0.5, 1.0), handlelength=1.5, columnspacing=1.0)
fig.tight_layout(rect=(0, 0, 1, 0.9))
savefig(fig, "dup_nn_val_test_to_train")

# ------------------------------------------------------------------ 4. spatial leakage
srcs = {"main_train": df.group == "main_train", "pilot": df.group == "pilot", "train_extra": df.group.isin(["te_top_score", "te_random"])}
RAD = (15, 25, 40, 100)
rows = []
for sp in ("val", "test", "val+test"):
    vi = np.where(df.split.isin(["val", "test"]) if sp == "val+test" else (df.split == sp) & (df.phase == "main"))[0]
    for sn, sm in srcs.items():
        si = np.where(sm)[0]
        dm = D[np.ix_(vi, si)].min(1)
        r = {"vt_split": sp, "n_vt_panos": len(vi), "train_side_source": sn, "n_source_panos": len(si), "min_dist_m": float(dm.min()),
             "median_nearest_m": float(np.median(dm))}
        r.update({f"n_vt_within_{t}m": int((dm < t).sum()) for t in RAD})
        r.update({f"pct_vt_within_{t}m": float(100 * (dm < t).mean()) for t in RAD})
        rows.append(r)
sp_tab = pd.DataFrame(rows)
sp_tab.to_csv(OUT_T / "dup_spatial_vt_to_train_side.csv", index=False, encoding="utf-8-sig")
N["spatial_vt_to_train_side"] = rows
# min distance between panos of different splits
mn = {}
for a, b in (("train", "val"), ("train", "test"), ("val", "test")):
    ia = np.where(df.split == a)[0] if a != "train" else np.where(is_train)[0]
    ib = np.where((df.split == b) & (df.phase == "main"))[0]
    sub = D[np.ix_(ia, ib)]
    k = np.unravel_index(sub.argmin(), sub.shape)
    mn[f"{a}-{b}"] = {"min_m": float(sub.min()), "items": [df.item[ia[k[0]]], df.item[ib[k[1]]]]}
N["min_distance_between_splits"] = mn
# pairs < 40 m
ii, jj = np.nonzero(D[np.ix_(vt_i, tr_i)] < 40)
rows = [{"vt_item": df.item[vt_i[a]], "vt_split": df.split[vt_i[a]], "vt_street": df.street_id[vt_i[a]], "vt_pano": df.parent_pano_id[vt_i[a]],
         "vt_position": df.position_group[vt_i[a]], "train_item": df.item[tr_i[b]], "train_group": df.group[tr_i[b]], "train_street": df.street_id[tr_i[b]],
         "train_pano": df.parent_pano_id[tr_i[b]], "train_position": df.position_group[tr_i[b]], "dist_m": float(D[vt_i[a], tr_i[b]]),
         "cosine": float(CS[vt_i[a], tr_i[b]]), "dhash": int(HD[vt_i[a], tr_i[b]]),
         "same_sequence": bool(df.sequence[vt_i[a]] == df.sequence[tr_i[b]])} for a, b in zip(ii, jj)]
P40 = pd.DataFrame(rows).sort_values("dist_m") if rows else pd.DataFrame(columns=["vt_item"])
P40.to_csv(OUT_T / "dup_spatial_pairs_lt40m.csv", index=False, encoding="utf-8-sig")
if len(ii):
    oo = np.argsort(D[vt_i[ii], tr_i[jj]], kind="stable")[:20]
    sheet(mk([(vt_i[ii[o]], tr_i[jj[o]]) for o in oo]), "dup_sheet_cross_split_closest_in_space_top20", 4, 240)
# close pairs of panos (any split): same place seen twice?
for rad in (5, 10, 15):
    cl = tri & (D < rad)
    ci, cj = np.nonzero(cl)
    kk = np.minimum(g[ci], g[cj]) * 6 + np.maximum(g[ci], g[cj])
    N[f"pairs_closer_than_{rad}m"] = {"all": int(len(ci)), "same_day": int((day[ci] == day[cj]).sum()), "same_position_group": int(same_pos[ci, cj].sum()),
                                      "by_group_pair": {f"{GROUPS[k // 6]}|{GROUPS[k % 6]}": int(c) for k, c in zip(*np.unique(kk, return_counts=True))}}
ci, cj = np.nonzero(tri & (D < 10))
pd.DataFrame({"item_a": df.item[ci].values, "group_a": df.group[ci].values, "street_a": df.street_id[ci].values, "item_b": df.item[cj].values, "group_b": df.group[cj].values,
              "street_b": df.street_id[cj].values, "dist_m": D[ci, cj], "same_position_group": same_pos[ci, cj], "same_day": day[ci] == day[cj], "cosine": CS[ci, cj],
              "dhash": HD[ci, cj]}).sort_values("dist_m").to_csv(OUT_T / "dup_spatial_pairs_lt10m_all_splits.csv", index=False, encoding="utf-8-sig")
if len(P40):
    sp40 = (P40.groupby(["vt_split", "vt_street", "train_group", "train_street"]).agg(n_pairs=("dist_m", "size"), min_dist_m=("dist_m", "min"), max_cosine=("cosine", "max"))
            .reset_index().sort_values("min_dist_m"))
    sp40.to_csv(OUT_T / "dup_spatial_street_pairs_lt40m.csv", index=False, encoding="utf-8-sig")
N["pairs_lt40m"] = {"n_pairs": len(P40), "by_train_group": P40.train_group.value_counts().to_dict() if len(P40) else {},
                    "n_vt_panos_involved": int(P40.vt_item.nunique()) if len(P40) else 0,
                    "n_train_panos_involved": int(P40.train_item.nunique()) if len(P40) else 0,
                    "max_cosine_among_pairs": float(P40.cosine.max()) if len(P40) else None,
                    "min_dhash_among_pairs": int(P40.dhash.min()) if len(P40) else None}
# documented 40 m rule for train_extra
te_i = np.where(srcs["train_extra"])[0]
vt_main = np.where(df.split.isin(["val", "test"]) & (df.phase == "main"))[0]
dte = D[np.ix_(te_i, vt_main)].min(1)
N["train_extra_40m_rule"] = {"n_train_extra": len(te_i), "min_dist_to_val_test_m": float(dte.min()), "n_below_40m": int((dte < 40).sum()),
                             "n_below_39_5m": int((dte < 39.5).sum()), "items_below_40m": df.item[te_i[dte < 40]].tolist(),
                             "quantiles_nearest_vt_m": {f"q{q}": float(np.quantile(dte, q)) for q in (0, 0.01, 0.05, 0.5)}}
# shared identifiers
sets = {s: set(df.street_id[df.split == s]) for s in ("train", "val", "test")}
base = lambda s: s.split("#")[0]  # noqa: E731  (street_id "Name#k" = k-th segment of one named street)
bsets = {s: {base(v) for v in vals} for s, vals in sets.items()}
ps = {s: set(df.position_group[(df.split == s) & pos_has]) for s in ("train", "val", "test")}
pano = {s: set(df.parent_pano_id[df.split == s]) for s in ("train", "val", "test")}
N["shared_ids"] = {
    "street_id_train_val": sorted(sets["train"] & sets["val"]), "street_id_train_test": sorted(sets["train"] & sets["test"]), "street_id_val_test": sorted(sets["val"] & sets["test"]),
    "street_name_without_segment_train_val": sorted(bsets["train"] & bsets["val"]), "street_name_without_segment_train_test": sorted(bsets["train"] & bsets["test"]),
    "street_name_without_segment_val_test": sorted(bsets["val"] & bsets["test"]),
    "position_group_train_val": len(ps["train"] & ps["val"]), "position_group_train_test": len(ps["train"] & ps["test"]), "position_group_val_test": len(ps["val"] & ps["test"]),
    "parent_pano_train_val": len(pano["train"] & pano["val"]), "parent_pano_train_test": len(pano["train"] & pano["test"]), "parent_pano_val_test": len(pano["val"] & pano["test"]),
    "n_streets": {s: len(v) for s, v in sets.items()}}
# main-train vs train_extra: same street ids? (train_extra streets are train streets by design)
N["shared_ids"]["street_ids_main_train_and_train_extra"] = len(set(df.street_id[df.group == "main_train"]) & set(df.street_id[srcs["train_extra"]]))
N["shared_ids"]["street_ids_pilot_and_main_train"] = len(set(df.street_id[df.group == "pilot"]) & set(df.street_id[df.group == "main_train"]))
sq = df.groupby("sequence").agg(n=("item", "size"), n_split=("split", "nunique"), splits=("split", lambda s: "|".join(sorted(set(s)))),
                                groups=("group", lambda s: "|".join(sorted(set(s)))), n_streets=("street_id", "nunique")).reset_index()
sq.to_csv(OUT_T / "dup_sequences.csv", index=False, encoding="utf-8-sig")
shared_sq = sq[sq.splits.str.contains("train") & sq.splits.str.contains("val|test")]
seq_vt = set(df.sequence[is_vt]) & set(df.sequence[is_train])
vt_with_seq = df[is_vt & df.sequence.isin(seq_vt)]
N["sequences"] = {"n_sequences": len(sq), "n_shared_train_and_valtest": len(shared_sq), "n_val_test_crops_in_shared_sequence": len(vt_with_seq),
                  "by_split": vt_with_seq.split.value_counts().to_dict(), "n_sequences_in_both_val_and_test": int((sq.splits.str.contains("val") & sq.splits.str.contains("test")).sum()),
                  "items_val_test_in_shared_sequence": vt_with_seq.item.tolist()}
shared_sq.to_csv(OUT_T / "dup_sequences_shared_train_valtest.csv", index=False, encoding="utf-8-sig")
vt_with_seq[["item", "group", "street_id", "sequence"]].to_csv(OUT_T / "dup_valtest_items_in_shared_sequence.csv", index=False, encoding="utf-8-sig")
# map
fig, ax = plt.subplots(figsize=(6.4, 6.4))
for k, (grs, c, s, a, z) in {"train_extra": (["te_top_score", "te_random"], GCOL["te_random"], 3, 0.5, 1), "main (train)": (["main_train"], GCOL["main_train"], 3, 0.6, 2),
                            "pilot (train)": (["pilot"], GCOL["pilot"], 5, 0.9, 3), "val": (["val"], GCOL["val"], 7, 0.9, 4), "test": (["test"], GCOL["test"], 7, 0.9, 5)}.items():
    m = df.group.isin(grs).to_numpy()
    ax.scatter(df.lon[m], df.lat[m], s=s, c=c, alpha=a, lw=0, zorder=z, label=f"{k} (n={m.sum():,})")
ax.set_aspect(1 / np.cos(np.radians(LAT0)))  # equal metric scale in x and y
ax.set_xlabel("Kinh độ (°E)"), ax.set_ylabel("Vĩ độ (°N)")
ax.legend(loc="upper left", frameon=True, framealpha=0.9, markerscale=2)
ax.text(0.99, 0.01, "Mỗi chấm = một pano; tỉ lệ x:y theo mét", transform=ax.transAxes, ha="right", va="bottom", fontsize=7)
fig.tight_layout()
savefig(fig, "dup_map_positions")

# ------------------------------------------------------------------ 5. diversity
rows = []
rng = np.random.default_rng(0)
for k in GROUPS:
    ix = np.where(df.group == k)[0]
    sub = CS[np.ix_(ix, ix)].astype(np.float64)
    off = ~np.eye(len(ix), dtype=bool)
    ss = street[ix][:, None] == street[ix][None, :]
    nnc = np.where(off, sub, -1).max(1)
    nn_other = np.where(off & ~ss, sub, -1).max(1)
    ev = []
    for _ in range(20 if len(ix) > 150 else 1):
        s_ = rng.choice(len(ix), 150, replace=False) if len(ix) > 150 else np.arange(len(ix))
        z = X[ix[s_]] - X[ix[s_]].mean(0)
        lam = np.clip(np.linalg.eigvalsh(z @ z.T), 0, None)
        p = lam / lam.sum()
        ev.append(float(np.exp(-(p[p > 0] * np.log(p[p > 0])).sum())))
    rows.append({"group": k, "n": len(ix), "n_streets": int(df.street_id[ix].nunique()), "crops_per_street_median": float(df[df.group == k].groupby("street_id").size().median()),
                 "mean_pairwise_cos": float(sub[off].mean()), "mean_cos_same_street": float(sub[off & ss].mean()) if (off & ss).any() else np.nan,
                 "mean_cos_other_street": float(sub[off & ~ss].mean()) if (off & ~ss).any() else np.nan, "mean_nn_cos_within_group": float(nnc.mean()),
                 "mean_nn_cos_other_street_within_group": float(nn_other.mean()), "effective_rank_150_subsample": float(np.mean(ev))})
div = pd.DataFrame(rows)
div.to_csv(OUT_T / "dup_diversity_by_group.csv", index=False, encoding="utf-8-sig")
N["diversity"] = div.set_index("group").to_dict("index")
gm = np.zeros((6, 6))
for a in range(6):
    for b in range(6):
        ia, ib = np.where(g == a)[0], np.where(g == b)[0]
        s_ = CS[np.ix_(ia, ib)].astype(np.float64)
        gm[a, b] = (s_.sum() - (len(ia) if a == b else 0)) / (s_.size - (len(ia) if a == b else 0))
pd.DataFrame(gm, index=GROUPS, columns=GROUPS).to_csv(OUT_T / "dup_group_mean_cosine_matrix.csv", encoding="utf-8-sig")
cen = np.stack([X[g == a].mean(0) for a in range(6)])
cen /= np.linalg.norm(cen, axis=1, keepdims=True)
pd.DataFrame(cen @ cen.T, index=GROUPS, columns=GROUPS).to_csv(OUT_T / "dup_group_centroid_cosine_matrix.csv", encoding="utf-8-sig")
fig, ax = plt.subplots(figsize=(4.8, 3.9))
im = ax.imshow(gm, cmap="viridis")
ax.set_xticks(range(6)), ax.set_yticks(range(6))
ax.set_xticklabels([GNAME[k] for k in GROUPS], rotation=40, ha="right"), ax.set_yticklabels([GNAME[k] for k in GROUPS])
for a in range(6):
    for b in range(6):
        ax.text(b, a, f"{gm[a, b]:.2f}", ha="center", va="center", color="white" if gm[a, b] < gm.mean() else "black", fontsize=7)
ax.spines[:].set_visible(False)
fig.colorbar(im, ax=ax, label="Cosine trung bình giữa các cặp ảnh", fraction=0.046)
fig.tight_layout()
savefig(fig, "dup_group_cosine_heatmap")

# t-SNE
from sklearn.decomposition import PCA  # noqa: E402
from sklearn.manifold import TSNE  # noqa: E402

log("t-SNE ...")
Z = TSNE(n_components=2, perplexity=30, init="pca", learning_rate="auto", random_state=0).fit_transform(PCA(50, random_state=0).fit_transform(X))
pd.DataFrame({"item": df.item, "group": df.group, "label": df.label, "tsne_x": Z[:, 0], "tsne_y": Z[:, 1]}).to_csv(OUT_T / "dup_tsne_coords.csv", index=False, encoding="utf-8-sig")
fig, ax = plt.subplots(1, 2, figsize=(6.8, 3.7))
order = {"te_random": 0, "te_top_score": 1, "main_train": 2, "pilot": 3, "val": 4, "test": 5}
for k in sorted(GROUPS, key=order.get):
    m = (df.group == k).to_numpy()
    ax[0].scatter(Z[m, 0], Z[m, 1], s=2.5, c=GCOL[k], alpha=0.6, lw=0, label=f"{GNAME[k]} ({m.sum():,})", rasterized=True)
perm = np.random.default_rng(1).permutation(n)
for lb in ("0", "I", "1"):
    m = (df.label == lb).to_numpy()
    ax[1].scatter(Z[m, 0], Z[m, 1], s=2.5, c=LCOL[lb], alpha=0.6, lw=0, label={"0": "0 thông được", "1": "1 bị chặn", "I": "I thiếu thông tin"}[lb] + f" ({m.sum():,})", rasterized=True)
for a_, t in zip(ax, ("Theo nhóm dữ liệu", "Theo nhãn (chỉ để tô màu)")):
    a_.set_xticks([]), a_.set_yticks([]), a_.set_title(t), a_.spines[:].set_visible(False)
    a_.legend(loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=2, frameon=False, markerscale=3, fontsize=6.5, handletextpad=0.2, columnspacing=0.8)
fig.tight_layout()
savefig(fig, "dup_tsne")

# domain classifier (no labels): street-grouped cross-validated AUC
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402
from sklearn.model_selection import StratifiedGroupKFold  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402


def domain_auc(ia, ib, groups, k=5, repeats=3):
    """Street-grouped, class-stratified CV (repeated with 3 different fold partitions); returns mean fold AUC over all folds."""
    idx = np.r_[ia, ib]
    yy = np.r_[np.zeros(len(ia)), np.ones(len(ib))]
    gg = groups[idx]
    fold_auc, pooled = [], []
    for rep in range(repeats):
        oof = np.zeros(len(idx))
        for tr, te in StratifiedGroupKFold(min(k, len(set(gg))), shuffle=True, random_state=rep).split(idx, yy, gg):
            clf = make_pipeline(StandardScaler(), LogisticRegression(C=0.01, class_weight="balanced", max_iter=1000)).fit(X[idx[tr]], yy[tr])
            oof[te] = clf.decision_function(X[idx[te]])
            if len(set(yy[te])) == 2:
                fold_auc.append(roc_auc_score(yy[te], oof[te]))
        pooled.append(roc_auc_score(yy, oof))
    return {"n_a": len(ia), "n_b": len(ib), "n_street_groups": len(set(gg)), "auc_pooled_oof": float(np.mean(pooled)), "auc_fold_mean": float(np.mean(fold_auc)),
            "auc_fold_sd": float(np.std(fold_auc)), "auc_min_fold": float(np.min(fold_auc)), "auc_max_fold": float(np.max(fold_auc)), "n_folds_total": len(fold_auc)}


G_ = lambda *ks: np.where(df.group.isin(ks))[0]  # noqa: E731
tasks = {"main_train vs train_extra (all)": (G_("main_train"), G_("te_top_score", "te_random")),
         "main_train vs train_extra top_score": (G_("main_train"), G_("te_top_score")),
         "main_train vs train_extra random": (G_("main_train"), G_("te_random")),
         "main_train vs pilot": (G_("main_train"), G_("pilot")),
         "main_train vs val+test": (G_("main_train"), G_("val", "test")),
         "train_extra vs val+test": (G_("te_top_score", "te_random"), G_("val", "test")),
         "main_train vs val": (G_("main_train"), G_("val")), "main_train vs test": (G_("main_train"), G_("test")),
         "val vs test": (G_("val"), G_("test")),
         "train_extra top_score vs random": (G_("te_top_score"), G_("te_random"))}
log("domain classifiers ...")
rows = []
for nm, (ia, ib) in tasks.items():
    r = {"task": nm, **domain_auc(ia, ib, street)}
    rows.append(r)
    log(nm, r)
# null: main_train streets randomly assigned to two pseudo-domains
mt = G_("main_train")
us = np.unique(street[mt])
nulls = []
for sd in range(5):
    half = set(np.random.default_rng(sd).permutation(us)[: len(us) // 2])
    ia, ib = mt[[street[i] not in half for i in mt]], mt[[street[i] in half for i in mt]]
    nulls.append(domain_auc(ia, ib, street))
rows.append({"task": "NULL: main_train streets randomly split in 2 (mean of 5 seeds)", "n_a": int(np.mean([r_["n_a"] for r_ in nulls])), "n_b": int(np.mean([r_["n_b"] for r_ in nulls])),
             "auc_pooled_oof": float(np.mean([r_["auc_pooled_oof"] for r_ in nulls])), "auc_fold_mean": float(np.mean([r_["auc_fold_mean"] for r_ in nulls])),
             "auc_fold_sd": float(np.std([r_["auc_fold_mean"] for r_ in nulls])), "n_folds_total": 5})
# null 2: train_extra streets randomly split
te = G_("te_top_score", "te_random")
us = np.unique(street[te])
nulls = []
for sd in range(5):
    half = set(np.random.default_rng(sd).permutation(us)[: len(us) // 2])
    nulls.append(domain_auc(te[[street[i] not in half for i in te]], te[[street[i] in half for i in te]], street))
rows.append({"task": "NULL: train_extra streets randomly split in 2 (mean of 5 seeds)", "n_a": int(np.mean([r_["n_a"] for r_ in nulls])), "n_b": int(np.mean([r_["n_b"] for r_ in nulls])),
             "auc_pooled_oof": float(np.mean([r_["auc_pooled_oof"] for r_ in nulls])), "auc_fold_mean": float(np.mean([r_["auc_fold_mean"] for r_ in nulls])),
             "auc_fold_sd": float(np.std([r_["auc_fold_mean"] for r_ in nulls])), "n_folds_total": 5})
dom = pd.DataFrame(rows)
dom.to_csv(OUT_T / "dup_domain_classifier_auc.csv", index=False, encoding="utf-8-sig")
N["domain_auc"] = dom.set_index("task").to_dict("index")
N["domain_auc_method"] = "StandardScaler + LogisticRegression(C=0.01, balanced) on DINOv2 embeddings, 5-fold StratifiedGroupKFold (shuffle, 3 repeats) by street_id, no labels used"

(OUT_T / "duplicate_numbers.json").write_text(json.dumps(jsonable(N), ensure_ascii=False, indent=1), encoding="utf-8")
df.drop(columns=["path", "latlon"]).to_csv(OUT_T / "dup_item_hashes.csv", index=False, encoding="utf-8-sig")
log("done")
