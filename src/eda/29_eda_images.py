"""EDA of the image pixels of the 5,149 labelled crops (main 2,999 + pilot 150 + train_extra 2,000). Descriptive only:
no label, split or threshold is changed or tuned; val/test labels are used for descriptive statistics only.

Groups, always reported separately:
  main_train / main_val / main_test  phase main (natural sampling), by split
  pilot                              150 crops, train, non-natural (stratified) sampling
  extra_top_score / extra_random     train_extra v2 labels, selector-chosen (biased), by stratum
Labels: 0 = Con loi di, 1 = Bi chan, I = Khong du thong tin (excluded from the model).

Inputs (read-only):
  data/labels/main_labels_v1.csv, data/labels/train_extra_labels_v2.csv  (item, file, split, street_id, label, reason...)
  data/labels/train_extra_report/train_extra_labels.csv  (reasons of the v1 train_extra labels; v2 kept the reasons)
  data/manifest/main_v1.csv, pilot_v2.csv, train_extra_v1.csv  (brightness of the PANO's upper half = night filter)
  data/manifest/main_v1_collection_status.csv  (3,057 panos, 58 rejected as night)
  data/crops/<file>  (crop pixels); src/enrich.py fetch_pano (equirectangular panos, cached in data/raw/pano)
Crops on this PC are a mix of server copies and re-projections from the pano (JPEG re-encoding differs by ~1.4 grey
levels); the two kinds are not separated here.

Per-image measures (decoded RGB image, 640x640, values 0-255; "grey" = Pillow convert("L") = Rec.601,
G = 0.299 R + 0.587 G + 0.114 B, rounded to uint8):
  lum          mean of grey
  contrast     RMS contrast = population std of grey
  dark_share   share of pixels with grey < 30
  sat_share    share of pixels with grey > 245 (saturated / burnt-out; NOT colour saturation)
  sharpness    variance of the Laplacian of grey (4-neighbour kernel [[0,1,0],[1,-4,1],[0,1,0]], border = mirror, i.e.
               scipy.ndimage.laplace(mode="mirror") = cv2.Laplacian(ksize=1, BORDER_REFLECT_101)); higher = sharper
  colourfulness  Hasler & Suesstrunk (2003): rg = R-G, yb = 0.5(R+G)-B,
               sqrt(std(rg)^2 + std(yb)^2) + 0.3 sqrt(mean(rg)^2 + mean(yb)^2)
  saturation   mean HSV saturation, S = (max-min)/max per pixel (0 where max = 0), range 0-1
  lum_upper / lum_lower  mean grey of rows 0-319 / 320-639 (the sidewalk is mostly in the lower half)
  lum_lower_minus_upper  lum_lower - lum_upper
  rgbmean_upper  mean of all three channels over rows 0-319; same formula as the night filter, which uses
               e[:h//2].mean() on the pano (mean over R, G, B, NOT Rec.601 grey), so this is the crop counterpart of the
               manifest `brightness`
  file_kb      file size / 1024; jpeg_q = IJG quality estimated from the luminance quantisation table
Effect sizes: AUC(a vs b) = P(X_a > X_b) + 0.5 P(X_a = X_b) (0.5 = no difference); smd_iqr = (median_a - median_b) /
mean(IQR_a, IQR_b). The 95% interval is a CLUSTER bootstrap over street_id (resampling streets with all their crops,
300 draws, seed fixed). Crops of one street are correlated, so no i.i.d. p-values are reported.
Outlier fences: Tukey, computed once over ALL readable crops (Q1 - k IQR, Q3 + k IQR; k = 1.5 and 3); sharpness is also
fenced on log10(sharpness) because it is heavily right-skewed. Nothing is removed.

Usage: .venv\\Scripts\\python.exe src/eda/29_eda_images.py     (cache: image_stats.csv; delete it to recompute)
Outputs (docs/data_report/): tables/image_stats.csv (one row per crop, also the cache), image_summary_stats.csv,
image_effect_sizes.csv, image_spearman_brightness.csv, image_outliers.csv, image_outlier_counts.csv,
image_reason_blur_dark.csv, image_reason_blur_dark_summary.csv, image_format_check.csv, image_night_check.csv,
image_numbers.json; figures/img_*.pdf (+ preview PNGs in figures/preview/), figures/img_*.jpg (sheets, grids)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, enrich.py

import json
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage, stats

from common import DATA, ROOT

OUT = ROOT / "docs" / "data_report"
TAB, FIG = OUT / "tables", OUT / "figures"
PREV = FIG / "preview"
for d in (TAB, FIG, PREV):
    d.mkdir(parents=True, exist_ok=True)

GROUPS = ["main_train", "main_val", "main_test", "pilot", "extra_top_score", "extra_random"]
GLAB = {"main_train": "main train", "main_val": "main val", "main_test": "main test", "pilot": "pilot",
        "extra_top_score": "extra top_score", "extra_random": "extra random"}
EXPECT = {"main_train": 1839, "main_val": 486, "main_test": 674, "pilot": 150, "extra_top_score": 1400, "extra_random": 600}
LABELS = ["0", "1", "I"]
COL = {"0": "#4C78A8", "1": "#E45756", "I": "#9D9D9D"}
LNAME = {"0": "Còn lối đi (0)", "1": "Bị chặn (1)", "I": "Không đủ thông tin (I)"}
MEAS = ["lum", "contrast", "dark_share", "sat_share", "sharpness", "colourfulness", "saturation", "lum_lower",
        "lum_upper", "file_kb"]
MEAS_ALL = MEAS + ["lum_lower_minus_upper", "rgbmean_upper"]
BLUR = "Ảnh mờ / tối / cháy sáng"
NBOOT, SEED = 300, 20261114
FONT = str(Path(__import__("matplotlib").__file__).parent / "mpl-data" / "fonts" / "ttf" / "DejaVuSans.ttf")

# IJG standard luminance quantisation table (Annex K), used to estimate the JPEG quality from the file's own table
STD_Q = np.array([16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55, 14, 13, 16, 24, 40, 57, 69, 56, 14, 17,
                  22, 29, 51, 87, 80, 62, 18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92, 49, 64, 78,
                  87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99])


def _q_sum(q):
    s = 5000 / q if q < 50 else 200 - 2 * q
    return np.clip((STD_Q * s + 50) // 100, 1, 255).sum()


Q_SUMS = np.array([_q_sum(q) for q in range(1, 101)])


def measure(path):
    """Worker: format facts and pixel measures of one crop. Never raises."""
    p = Path(path)
    d = {"exists": p.exists(), "open_ok": False, "error": ""}
    if not d["exists"]:
        d["error"] = "missing"
        return d
    st = p.stat()
    d["file_bytes"], d["mtime_ns"] = st.st_size, st.st_mtime_ns
    try:
        im = Image.open(p)
        d["format"], d["mode"] = im.format, im.mode
        d["width"], d["height"] = im.size
        qt = getattr(im, "quantization", None)
        if qt and 0 in qt:
            d["jpeg_q"] = int(np.argmin(np.abs(Q_SUMS - sum(qt[0]))) + 1)
        rgb = im.convert("RGB")
        im.close()
        a = np.asarray(rgb, dtype=np.float64)
        grey8 = np.asarray(rgb.convert("L"))
        g = grey8.astype(np.float64)
        h2 = g.shape[0] // 2
        R, G, B = a[..., 0], a[..., 1], a[..., 2]
        rg, yb = R - G, 0.5 * (R + G) - B
        mx, mn = a.max(axis=2), a.min(axis=2)
        sat = np.where(mx > 0, (mx - mn) / np.where(mx > 0, mx, 1), 0.0)
        d.update(
            lum=g.mean(), contrast=g.std(), dark_share=(grey8 < 30).mean(), sat_share=(grey8 > 245).mean(),
            sharpness=ndimage.laplace(g, mode="mirror").var(),
            colourfulness=np.hypot(rg.std(), yb.std()) + 0.3 * np.hypot(rg.mean(), yb.mean()),
            saturation=sat.mean(), lum_upper=g[:h2].mean(), lum_lower=g[h2:].mean(),
            rgbmean_upper=a[:h2].mean(), file_kb=st.st_size / 1024)
        d["lum_lower_minus_upper"] = d["lum_lower"] - d["lum_upper"]
        d["open_ok"] = True
    except Exception as e:  # noqa: BLE001
        d["error"] = f"{type(e).__name__}: {e}"[:200]
    return d


# ----------------------------------------------------------------------------------------------- data
def load_meta():
    rd = lambda p, **k: pd.read_csv(p, encoding="utf-8-sig", dtype={"item": str, "label": str}, **k)
    m = rd(DATA / "labels" / "main_labels_v1.csv")
    t = rd(DATA / "labels" / "train_extra_labels_v2.csv")
    rep = rd(DATA / "labels" / "train_extra_report" / "train_extra_labels.csv")[["item", "reason", "label"]]
    rep = rep.rename(columns={"reason": "reason_v1", "label": "label_v1_report"})
    t = t.drop(columns=["reason"]).merge(rep, on="item", how="left").rename(columns={"reason_v1": "reason"})
    m["group"] = np.where(m.phase == "pilot", "pilot", "main_" + m.split)
    t["group"] = "extra_" + t.stratum
    cols = ["item", "phase", "file", "group", "split", "street_id", "label", "source", "reason"]
    df = pd.concat([m[cols], t[cols + ["stratum", "score"]]], ignore_index=True)
    bri = pd.concat([rd(DATA / "manifest" / f)[["item", "brightness", "captured_at", "creator"]]
                     for f in ("main_v1.csv", "pilot_v2.csv", "train_extra_v1.csv")])
    df = df.merge(bri, on="item", how="left", validate="1:1")
    assert df.item.is_unique and df.brightness.notna().all(), "item/brightness join failed"
    df["group"] = pd.Categorical(df.group, GROUPS, ordered=True)
    return df.sort_values(["group", "item"]).reset_index(drop=True)


def compute_stats(df):
    """Per-image table, cached in tables/image_stats.csv (recomputed when file size/mtime changed or earlier failure)."""
    cache_p = TAB / "image_stats.csv"
    keep = ["file", "exists", "open_ok", "error", "file_bytes", "mtime_ns", "format", "mode", "width", "height",
            "jpeg_q"] + MEAS_ALL
    cache = None
    if cache_p.exists():
        cache = pd.read_csv(cache_p, encoding="utf-8-sig", usecols=lambda c: c in keep).drop_duplicates("file").set_index("file")
    paths = {f: DATA / "crops" / f for f in df.file}
    todo = []
    for f, p in paths.items():
        if cache is not None and f in cache.index and p.exists():
            c = cache.loc[f]
            if bool(c.open_ok) and c.file_bytes == p.stat().st_size and c.mtime_ns == p.stat().st_mtime_ns:
                continue
        todo.append(f)
    print(f"{len(df)} crops, {len(df) - len(todo)} from cache, {len(todo)} to compute", flush=True)
    new = {}
    if todo:
        with ProcessPoolExecutor(min(8, os.cpu_count() or 4)) as ex:
            for f, r in zip(todo, ex.map(measure, [str(paths[f]) for f in todo], chunksize=32)):
                new[f] = r
    rows = []
    for f in df.file:
        if f in new:
            r = {"file": f, **new[f]}
        else:
            r = {"file": f, **{k: v for k, v in cache.loc[f].items() if k in keep}}
        rows.append(r)
    S = pd.DataFrame(rows)
    for c in keep:
        if c not in S:
            S[c] = np.nan
    return df.merge(S[keep], on="file", how="left", validate="1:1")


# ----------------------------------------------------------------------------------------------- statistics
def describe(x):
    x = pd.Series(x).dropna().astype(float)
    if len(x) == 0:
        return dict(n=0)
    q1, q3 = x.quantile(0.25), x.quantile(0.75)
    return dict(n=len(x), mean=x.mean(), median=x.median(), variance=x.var(ddof=1) if len(x) > 1 else np.nan,
                min=x.min(), max=x.max(), q1=q1, q3=q3, iqr=q3 - q1)


def summary_table(S):
    rows = []
    pools = {g: S[S.group == g] for g in GROUPS}
    pools["main_all"] = S[S.group.isin(["main_train", "main_val", "main_test"])]
    pools["all_crops"] = S
    for g, d in pools.items():
        for lab in ["all"] + LABELS:
            dd = d if lab == "all" else d[d.label == lab]
            for m in MEAS_ALL:
                rows.append(dict(group=g, label=lab, measure=m, **describe(dd[m])))
    return pd.DataFrame(rows)


def auc_matrix(A, B):
    """AUC(a vs b) for each column; A, B 2-D arrays."""
    na, nb = len(A), len(B)
    r = stats.rankdata(np.vstack([A, B]), axis=0)
    return (r[:na].sum(axis=0) - na * (na + 1) / 2) / (na * nb)


def cluster_boot_auc(da, db, cols, rng):
    """Cluster bootstrap (streets) of AUC. da, db: DataFrames; resample the union of their streets."""
    streets = np.unique(np.concatenate([da.street_id.values, db.street_id.values]))
    ia = {s: i for s, i in da.reset_index(drop=True).groupby("street_id").indices.items()}
    ib = {s: i for s, i in db.reset_index(drop=True).groupby("street_id").indices.items()}
    A, B = da[cols].to_numpy(float), db[cols].to_numpy(float)
    out = []
    for _ in range(NBOOT):
        pick = rng.choice(streets, len(streets))
        xa = [ia[s] for s in pick if s in ia]
        xb = [ib[s] for s in pick if s in ib]
        if not xa or not xb:
            continue
        out.append(auc_matrix(A[np.concatenate(xa)], B[np.concatenate(xb)]))
    out = np.array(out)
    return np.percentile(out, 2.5, axis=0), np.percentile(out, 97.5, axis=0), len(out)


def effect_sizes(S):
    S = S[S.open_ok == True]  # noqa: E712
    rng = np.random.default_rng(SEED)
    comps = []  # (kind, stratum, name_a, name_b, DataFrame a, DataFrame b)
    main_all = S[S.group.isin(["main_train", "main_val", "main_test"])]
    for g, d in [(g, S[S.group == g]) for g in GROUPS] + [("main_all", main_all)]:
        for a, b in (("1", "0"), ("I", "0"), ("I", "1")):
            comps.append(("label_within_group", g, f"{a}", f"{b}", d[d.label == a], d[d.label == b]))
    pairs = [("main_val", "main_train"), ("main_test", "main_train"), ("main_test", "main_val"), ("pilot", "main_train"),
             ("extra_top_score", "main_train"), ("extra_random", "main_train"), ("extra_top_score", "extra_random")]
    for a, b in pairs:
        for lab in ["all"] + LABELS:
            da, db = S[S.group == a], S[S.group == b]
            if lab != "all":
                da, db = da[da.label == lab], db[db.label == lab]
            comps.append(("group_vs_group", lab, a, b, da, db))
    rows = []
    for kind, stratum, a, b, da, db in comps:
        if len(da) < 5 or len(db) < 5:
            for m in MEAS:
                rows.append(dict(kind=kind, stratum=stratum, a=a, b=b, measure=m, n_a=len(da), n_b=len(db)))
            continue
        auc = auc_matrix(da[MEAS].to_numpy(float), db[MEAS].to_numpy(float))
        lo, hi, nb = cluster_boot_auc(da, db, MEAS, rng)
        for k, m in enumerate(MEAS):
            qa, qb = da[m].quantile([.25, .75]).values, db[m].quantile([.25, .75]).values
            piqr = ((qa[1] - qa[0]) + (qb[1] - qb[0])) / 2
            rows.append(dict(kind=kind, stratum=stratum, a=a, b=b, measure=m, n_a=len(da), n_b=len(db),
                             streets_a=da.street_id.nunique(), streets_b=db.street_id.nunique(),
                             median_a=da[m].median(), median_b=db[m].median(), auc_a_gt_b=auc[k],
                             auc_lo=lo[k], auc_hi=hi[k], boot_draws=nb,
                             smd_iqr=(da[m].median() - db[m].median()) / piqr if piqr > 0 else np.nan))
    return pd.DataFrame(rows)


def spearman_brightness(S):
    S = S[S.open_ok == True]  # noqa: E712
    rng = np.random.default_rng(SEED + 1)
    pools = {g: S[S.group == g] for g in GROUPS}
    pools["main_all"] = S[S.group.isin(["main_train", "main_val", "main_test"])]
    pools["all_crops"] = S
    rows = []
    for g, d in pools.items():
        ids = {s: i for s, i in d.reset_index(drop=True).groupby("street_id").indices.items()}
        streets = np.array(list(ids))
        for m in ["lum", "rgbmean_upper", "lum_upper", "lum_lower"]:
            rho = stats.spearmanr(d.brightness, d[m]).statistic
            bs = []
            x, y = d.brightness.to_numpy(float), d[m].to_numpy(float)
            for _ in range(NBOOT):
                ix = np.concatenate([ids[s] for s in rng.choice(streets, len(streets))])
                bs.append(stats.spearmanr(x[ix], y[ix]).statistic)
            rows.append(dict(group=g, crop_measure=m, n=len(d), spearman_rho=rho,
                             rho_lo=np.nanpercentile(bs, 2.5), rho_hi=np.nanpercentile(bs, 97.5),
                             brightness_min=d.brightness.min(), brightness_median=d.brightness.median(),
                             brightness_max=d.brightness.max()))
    return pd.DataFrame(rows)


def fences(S):
    S = S[S.open_ok == True].copy()  # noqa: E712
    S["log10_sharpness"] = np.log10(S.sharpness.where(S.sharpness > 0))
    F = {}
    for m in ["lum", "contrast", "sharpness", "log10_sharpness"]:
        q1, q3 = S[m].quantile(.25), S[m].quantile(.75)
        F[m] = dict(q1=q1, q3=q3, iqr=q3 - q1, low15=q1 - 1.5 * (q3 - q1), high15=q3 + 1.5 * (q3 - q1),
                    low3=q1 - 3 * (q3 - q1), high3=q3 + 3 * (q3 - q1))
    return S, F


def outliers(S):
    S, F = fences(S)
    for m, f in F.items():
        v = S[m]
        S[f"flag_{m}"] = np.select(
            [v < f["low3"], v < f["low15"], v > f["high3"], v > f["high15"]],
            ["low_3", "low_1.5", "high_3", "high_1.5"], default="")
    flags = [f"flag_{m}" for m in F]
    anyf = (S[flags] != "").any(axis=1)
    out = S[anyf][["item", "group", "label", "reason", "file", "lum", "contrast", "sharpness", "log10_sharpness"] + flags]
    rows = []
    for g in GROUPS + ["all_crops"]:
        for lab in ["all"] + LABELS:
            d = S if g == "all_crops" else S[S.group == g]
            d = d if lab == "all" else d[d.label == lab]
            for m in F:
                fl = d[f"flag_{m}"]
                rows.append(dict(group=g, label=lab, measure=m, n=len(d), n_low_beyond_1_5=int(fl.str.startswith("low").sum()),
                                 n_high_beyond_1_5=int(fl.str.startswith("high").sum()),
                                 n_low_beyond_3=int((fl == "low_3").sum()), n_high_beyond_3=int((fl == "high_3").sum())))
    return S, F, out, pd.DataFrame(rows)


def reason_check(S, F):
    """Do crops labelled I with reason 'blur / dark / burnt-out' sit in the tails? Percentile rank within the crops of the
    same phase pool (main / pilot / train_extra), AUC against all other crops of that pool, and global Tukey flags."""
    S = S.copy()
    S["pool"] = np.where(S.group.astype(str).str.startswith("main"), "main", np.where(S.group == "pilot", "pilot", "train_extra"))
    sel = S[(S.label == "I") & (S.reason == BLUR)].copy()
    meas = ["lum", "contrast", "dark_share", "sat_share", "sharpness", "colourfulness", "saturation"]
    for m in meas:
        sel["pct_" + m] = [stats.percentileofscore(S[S.pool == p][m], v, kind="mean") for p, v in zip(sel.pool, sel[m])]
    cols = ["item", "pool", "group", "label", "reason", "file"] + meas + ["pct_" + m for m in meas] + \
           [f"flag_{m}" for m in F]
    rows = []
    for pool in ["main", "pilot", "train_extra", "all"]:
        d = sel if pool == "all" else sel[sel.pool == pool]
        for m in meas:
            if len(d) == 0:
                continue
            res = dict(pool=pool, measure=m, n_reason=len(d), median_percentile=d["pct_" + m].median(),
                       share_below_p10=(d["pct_" + m] < 10).mean(), share_above_p90=(d["pct_" + m] > 90).mean(),
                       median_value=d[m].median())
            if pool != "all":
                P = S[S.pool == pool]
                rest = P[~P.item.isin(sel.item)]
                restI = rest[rest.label == "I"]
                res["auc_vs_all_other_crops"] = auc_matrix(d[[m]].to_numpy(float), rest[[m]].to_numpy(float))[0]
                res["n_other"] = len(rest)
                if len(restI):
                    res["auc_vs_other_I"] = auc_matrix(d[[m]].to_numpy(float), restI[[m]].to_numpy(float))[0]
                    res["n_other_I"] = len(restI)
            rows.append(res)
    return sel[cols].sort_values(["pool", "lum"]), pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------------- sheets
def font(sz):
    return ImageFont.truetype(FONT, sz)


def sheet(tiles, path, cols, tw, th, cap_h=36, fs=13, bg=(255, 255, 255)):
    """tiles: list of (PIL image, caption line 1, caption line 2). Saves a JPEG with long side <= 2000 px."""
    rows = -(-len(tiles) // cols)
    gap = 4
    W, H = cols * (tw + gap) + gap, rows * (th + cap_h + gap) + gap
    canvas = Image.new("RGB", (W, H), bg)
    dr = ImageDraw.Draw(canvas)
    f = font(fs)
    for k, (im, c1, c2) in enumerate(tiles):
        x, y = gap + (k % cols) * (tw + gap), gap + (k // cols) * (th + cap_h + gap)
        canvas.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
        dr.text((x + 2, y + th + 1), c1, fill=(0, 0, 0), font=f)
        dr.text((x + 2, y + th + 1 + fs + 3), c2, fill=(60, 60, 60), font=f)
    assert max(canvas.size) <= 2000, canvas.size
    canvas.save(path, quality=85)


def crop_sheet(S, order_col, ascending, path, value_fmt, n=24):
    d = S.sort_values([order_col, "item"], ascending=[ascending, True]).head(n)
    tiles = [(Image.open(DATA / "crops" / r.file).convert("RGB"), f"{r.item} {r.group} [{r.label}]",
              f"{order_col} = {value_fmt.format(getattr(r, order_col))}") for r in d.itertuples()]
    sheet(tiles, path, 6, 318, 318)


def fetch_thumb(pid):
    from enrich import fetch_pano
    e = fetch_pano(pid)
    if e is None:
        return None, np.nan
    return Image.fromarray(e), float(e[: e.shape[0] // 2].mean())


def night_check():
    cs = pd.read_csv(DATA / "manifest" / "main_v1_collection_status.csv", encoding="utf-8-sig", dtype={"id": str})
    night = cs[cs.status == "night"].sort_values(["brightness", "id"])
    kept = cs[(cs.status == "ok") & (cs.brightness >= 90)].sort_values(["brightness", "id"]).head(len(night))
    rows = []
    for name, d in (("rejected_night", night), ("kept_lowest", kept)):
        with ThreadPoolExecutor(8) as ex:
            res = list(ex.map(fetch_thumb, d.id))
        tiles = []
        for k, (r, (im, b2)) in enumerate(zip(d.itertuples(), res)):
            rows.append(dict(set=name, rank=k + 1, pano_id=r.id, street_id=r.street_id, split=r.split,
                             brightness_stored=r.brightness, brightness_recomputed_from_thumb=b2, fetched=im is not None))
            if im is None:
                im = Image.new("RGB", (2048, 1024), (255, 0, 255))
            tiles.append((im, f"{r.id}", f"brightness = {r.brightness}   (set {name[:3]}, #{k + 1})"))
        for part, sl in enumerate([tiles[:30], tiles[30:]]):
            sheet(sl, FIG / f"img_sheet_night_{name}_{part + 1}.jpg", 5, 394, 197, cap_h=34, fs=13)
    return pd.DataFrame(rows)


def example_grids(S):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans"})
    rng = np.random.default_rng(42)
    credit = "© Mapillary contributors, CC BY-SA 4.0"

    def draw(rows_spec, path, tag):
        fig, axes = plt.subplots(len(rows_spec), 6, figsize=(13, 2.15 * len(rows_spec) + 0.6), squeeze=False)
        for i, (name, d) in enumerate(rows_spec):
            pick = d.sort_values("item").iloc[rng.choice(len(d), 6, replace=False)]
            for j, r in enumerate(pick.itertuples()):
                ax = axes[i, j]
                ax.imshow(Image.open(DATA / "crops" / r.file).convert("RGB"))
                ax.set_xticks([]), ax.set_yticks([])
                for sp in ax.spines.values():
                    sp.set_visible(False)
                if tag:
                    ax.text(8, 40, r.label, color="white", fontsize=14, fontweight="bold", va="center",
                            bbox=dict(boxstyle="round,pad=0.2", fc=COL[r.label], ec="none"))
                if j == 0:
                    ax.set_ylabel(name, rotation=0, ha="right", va="center", fontsize=11, labelpad=8)
        fig.subplots_adjust(left=0.17, right=0.995, top=0.995, bottom=0.07, wspace=0.03, hspace=0.04)
        fig.text(0.5, 0.012, credit, ha="center", va="bottom", fontsize=10)
        fig.savefig(path, dpi=150, pil_kwargs={"quality": 85})
        plt.close(fig)
        assert max(Image.open(path).size) <= 2000

    tr = S[S.group == "main_train"]
    draw([(LNAME[l].replace(" (", "\n("), tr[tr.label == l]) for l in LABELS], FIG / "img_examples_main_train.jpg", False)
    ex = [("Tầng điểm cao\n(top_score)", S[S.group == "extra_top_score"]), ("Tầng ngẫu nhiên\n(random)", S[S.group == "extra_random"])]
    draw(ex, FIG / "img_examples_train_extra.jpg", True)


# ----------------------------------------------------------------------------------------------- figures
def figures(S):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42, "font.size": 10, "axes.titlesize": 11,
                         "axes.spines.top": False, "axes.spines.right": False})
    S = S[S.open_ok == True]  # noqa: E712
    main_all = S[S.group.isin(["main_train", "main_val", "main_test"])]

    def save(fig, name):
        fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
        fig.savefig(PREV / f"{name}.png", dpi=110, bbox_inches="tight")
        plt.close(fig)

    def dist(m, xlabel, name, log=False):
        fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 5.0), gridspec_kw={"width_ratios": [1.35, 1]})
        off = {"0": -0.27, "1": 0.0, "I": 0.27}
        for gi, g in enumerate(GROUPS):
            d = S[S.group == g]
            for lab in LABELS:
                v = d[d.label == lab][m].dropna()
                if len(v) == 0:
                    continue
                b = a1.boxplot(v, positions=[gi + off[lab]], widths=0.23, orientation="horizontal", patch_artist=True, showfliers=True,
                               flierprops=dict(marker=".", ms=2.5, mfc=COL[lab], mec=COL[lab], alpha=.5),
                               medianprops=dict(color="black", lw=1.4), whiskerprops=dict(lw=.8), capprops=dict(lw=.8),
                               boxprops=dict(lw=.8))
                b["boxes"][0].set(facecolor=COL[lab], alpha=.85)
        a1.set_yticks(range(len(GROUPS)))
        a1.set_yticklabels([f"{GLAB[g]}\n(n={int((S.group == g).sum()):,})".replace(",", ".") for g in GROUPS])
        a1.invert_yaxis()
        a1.set_xlabel(xlabel)
        a1.set_title("(a) Theo nhóm và nhãn (hộp: Q1–Q3, vạch: trung vị)", loc="left")
        if log:
            a1.set_xscale("log")
        a1.grid(axis="x", alpha=.25)
        from matplotlib.patches import Patch
        fig.legend(handles=[Patch(fc=COL[l], label=f"{LNAME[l]}") for l in LABELS], loc="lower center", ncol=3, fontsize=9.5,
                   frameon=False)
        allv = main_all[m].dropna()
        if log:
            bins = np.logspace(np.log10(max(allv[allv > 0].min(), 1e-3)), np.log10(allv.max()), 30)
        else:
            bins = np.linspace(allv.min(), allv.max(), 30)
        for lab in LABELS:
            v = main_all[main_all.label == lab][m].dropna()
            a2.hist(v, bins=bins, density=True, histtype="step", color=COL[lab], lw=1.8)
        if log:
            a2.set_xscale("log")
        a2.set_xlabel(xlabel)
        a2.set_ylabel("Mật độ")
        a2.set_title("(b) main tự nhiên (train+val+test), theo nhãn", loc="left")
        a2.grid(alpha=.25)
        fig.tight_layout(rect=(0, 0.06, 1, 1))
        save(fig, name)

    dist("lum", "Độ sáng trung bình (xám Rec.601, 0–255)", "img_dist_luminance")
    dist("contrast", "Độ tương phản RMS (độ lệch chuẩn của xám)", "img_dist_contrast")
    dist("sharpness", "Độ nét (phương sai Laplacian, thang log)", "img_dist_sharpness", log=True)
    dist("colourfulness", "Độ sặc sỡ màu (Hasler–Süsstrunk)", "img_dist_colourfulness")
    dist("file_kb", "Dung lượng tệp JPEG (KB)", "img_dist_filesize")

    # crop luminance vs pano brightness
    fig, axes = plt.subplots(2, 3, figsize=(11, 7.2), sharex=True, sharey=True)
    for ax, g in zip(axes.ravel(), GROUPS):
        d = S[S.group == g]
        for lab in ["I", "0", "1"]:
            dd = d[d.label == lab]
            ax.scatter(dd.brightness, dd.lum, s=7, alpha=.45, color=COL[lab], lw=0, label=LNAME[lab] if g == GROUPS[0] else None)
        rho = stats.spearmanr(d.brightness, d.lum).statistic
        ax.axvline(90, color="k", ls="--", lw=.9)
        ax.set_title(f"{GLAB[g]} (n={len(d):,}) – ρ = {rho:.2f}".replace(",", "."), fontsize=10)
        ax.grid(alpha=.25)
    fig.supxlabel("brightness của pano (trung bình RGB nửa trên của pano, đại lượng bộ lọc đêm dùng)", fontsize=10, y=0.06)
    for ax in axes[:, 0]:
        ax.set_ylabel("Độ sáng của ảnh crop (xám, 0–255)")
    from matplotlib.lines import Line2D
    fig.legend([Line2D([], [], marker="o", ls="", color=COL[l], ms=7) for l in LABELS], [LNAME[l] for l in LABELS],
               loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.0))
    fig.text(0.5, 1.0, "Vạch đứt: ngưỡng lọc đêm = 90. ρ = Spearman trong từng nhóm", ha="center", va="bottom", fontsize=9)
    fig.tight_layout(rect=(0, 0.1, 1, 0.98))
    save(fig, "img_lum_vs_pano_brightness")


# ----------------------------------------------------------------------------------------------- main
def main():
    df = load_meta()
    S = compute_stats(df)
    S.to_csv(TAB / "image_stats.csv", index=False, encoding="utf-8-sig", float_format="%.6g")
    N = {}

    # 1. format / validity
    ok = S[S.open_ok == True]  # noqa: E712
    grp_n = {g: int((S.group == g).sum()) for g in GROUPS}
    N["n_rows"] = len(S)
    N["n_per_group"] = grp_n
    N["n_per_group_expected_mismatch"] = {g: [grp_n[g], EXPECT[g]] for g in GROUPS if grp_n[g] != EXPECT[g]}
    N["n_per_group_label"] = {g: S[S.group == g].label.value_counts().reindex(LABELS).fillna(0).astype(int).to_dict() for g in GROUPS}
    bad = S[~(S.open_ok == True) | (S.width != 640) | (S.height != 640) | (S["mode"] != "RGB") | (S.file_bytes == 0)]  # noqa: E712
    N["format"] = dict(
        n_files=len(S), n_missing=int((S.exists != True).sum()), n_unreadable=int(((S.exists == True) & (S.open_ok != True)).sum()),  # noqa: E712
        n_zero_byte=int((S.file_bytes == 0).sum()), n_not_640x640=int(((ok.width != 640) | (ok.height != 640)).sum()),
        n_not_rgb=int((ok["mode"] != "RGB").sum()), n_not_jpeg=int((ok.format != "JPEG").sum()),
        n_any_problem=len(bad), missing_files=S[S.exists != True].file.tolist()[:50],
        file_kb=dict(min=ok.file_kb.min(), median=ok.file_kb.median(), max=ok.file_kb.max()),
        jpeg_q_counts={int(k): int(v) for k, v in ok.jpeg_q.value_counts().sort_index().items()})
    fc = S.groupby("group", observed=True).agg(n=("file", "size"), n_open_ok=("open_ok", lambda s: int((s == True).sum())),  # noqa: E712
                                               file_kb_median=("file_kb", "median"), file_kb_min=("file_kb", "min"),
                                               file_kb_max=("file_kb", "max"), jpeg_q_mode=("jpeg_q", lambda s: s.mode().iloc[0] if s.notna().any() else np.nan))
    fc.to_csv(TAB / "image_format_check.csv", encoding="utf-8-sig", float_format="%.6g")
    S = S[S.open_ok == True].copy()  # noqa: E712

    # 3. descriptive statistics, effect sizes, brightness
    summ = summary_table(S)
    summ.to_csv(TAB / "image_summary_stats.csv", index=False, encoding="utf-8-sig", float_format="%.6g")
    eff = effect_sizes(S)
    eff.to_csv(TAB / "image_effect_sizes.csv", index=False, encoding="utf-8-sig", float_format="%.6g")
    sp = spearman_brightness(S)
    sp.to_csv(TAB / "image_spearman_brightness.csv", index=False, encoding="utf-8-sig", float_format="%.6g")
    N["spearman_lum_vs_pano_brightness"] = {r.group: dict(n=r.n, rho=round(r.spearman_rho, 3), ci=[round(r.rho_lo, 3), round(r.rho_hi, 3)])
                                            for r in sp[sp.crop_measure == "lum"].itertuples()}
    N["spearman_rgbmean_upper_vs_pano_brightness"] = {r.group: dict(n=r.n, rho=round(r.spearman_rho, 3), ci=[round(r.rho_lo, 3), round(r.rho_hi, 3)])
                                                      for r in sp[sp.crop_measure == "rgbmean_upper"].itertuples()}
    N["pano_brightness_range_by_group"] = {r.group: [r.brightness_min, r.brightness_median, r.brightness_max]
                                           for r in sp[sp.crop_measure == "lum"].itertuples()}
    med = summ[summ.measure.isin(MEAS_ALL)].copy()
    N["median_by_group_label"] = {f"{r.group}|{r.label}|{r.measure}": dict(n=int(r.n), median=round(r.median, 4), q1=round(r.q1, 4), q3=round(r.q3, 4))
                                  for r in med.itertuples() if r.n and r.measure in ("lum", "contrast", "sharpness", "colourfulness")}
    key = eff[(eff.kind == "label_within_group") & eff.auc_a_gt_b.notna()]
    N["effect_label_auc"] = {f"{r.stratum}|{r.a}_vs_{r.b}|{r.measure}": [round(r.auc_a_gt_b, 3), round(r.auc_lo, 3), round(r.auc_hi, 3), int(r.n_a), int(r.n_b)]
                             for r in key.itertuples()}
    kg = eff[(eff.kind == "group_vs_group") & (eff.stratum == "all") & eff.auc_a_gt_b.notna()]
    N["effect_group_auc_all_labels"] = {f"{r.a}_vs_{r.b}|{r.measure}": [round(r.auc_a_gt_b, 3), round(r.auc_lo, 3), round(r.auc_hi, 3), int(r.n_a), int(r.n_b)]
                                        for r in kg.itertuples()}

    # 4. outliers
    S, F, out, ocnt = outliers(S)
    out.to_csv(TAB / "image_outliers.csv", index=False, encoding="utf-8-sig", float_format="%.6g")
    ocnt.to_csv(TAB / "image_outlier_counts.csv", index=False, encoding="utf-8-sig")
    N["fences"] = {m: {k: round(float(v), 4) for k, v in f.items()} for m, f in F.items()}
    N["outlier_counts_all_labels"] = {f"{r.group}|{r.measure}": dict(n=int(r.n), low_1_5=r.n_low_beyond_1_5, high_1_5=r.n_high_beyond_1_5,
                                                                       low_3=r.n_low_beyond_3, high_3=r.n_high_beyond_3)
                                      for r in ocnt[ocnt.label == "all"].itertuples()}
    N["n_crops_with_any_flag"] = len(out)
    hi = S[S.sat_share > 0.2]  # descriptive: crops with more than 20% burnt-out pixels, by group and street
    N["burnt_out_sat_share_gt_0.2"] = {g: dict(n=int((hi.group == g).sum()), share=round(float((hi.group == g).sum() / (S.group == g).sum()), 4),
                                               top_streets=hi[hi.group == g].street_id.value_counts().head(3).to_dict()) for g in GROUPS}
    crop_sheet(S, "lum", True, FIG / "img_sheet_darkest24.jpg", "{:.1f}")
    crop_sheet(S, "lum", False, FIG / "img_sheet_brightest24.jpg", "{:.1f}")
    crop_sheet(S, "sat_share", False, FIG / "img_sheet_most_saturated24.jpg", "{:.4f}")
    crop_sheet(S, "sharpness", True, FIG / "img_sheet_blurriest24.jpg", "{:.1f}")
    crop_sheet(S, "contrast", True, FIG / "img_sheet_lowest_contrast24.jpg", "{:.1f}")

    # reason check
    rc, rs = reason_check(S, F)
    rc.to_csv(TAB / "image_reason_blur_dark.csv", index=False, encoding="utf-8-sig", float_format="%.6g")
    rs.to_csv(TAB / "image_reason_blur_dark_summary.csv", index=False, encoding="utf-8-sig", float_format="%.6g")
    N["reason_blur_dark"] = {"n_by_group": rc.group.astype(str).value_counts().to_dict(),
                             "summary": {f"{r.pool}|{r.measure}": dict(n=r.n_reason, median_percentile=round(r.median_percentile, 1),
                                                                        auc_vs_all_other=None if pd.isna(getattr(r, "auc_vs_all_other_crops", np.nan)) else round(r.auc_vs_all_other_crops, 3),
                                                                        auc_vs_other_I=None if pd.isna(getattr(r, "auc_vs_other_I", np.nan)) else round(r.auc_vs_other_I, 3))
                                         for r in rs.itertuples()}}
    d = S[S.item.isin(rc.item)].sort_values(["group", "lum"])
    sheet([(Image.open(DATA / "crops" / r.file).convert("RGB"), f"{r.item} {r.group} [I]",
            f"lum {r.lum:.0f} con {r.contrast:.0f} sharp {r.sharpness:.0f}") for r in d.itertuples()],
          FIG / "img_sheet_reason_blur_dark.jpg", 7, 270, 270)

    # 5. night filter spot check
    try:
        nc = night_check()
        nc.to_csv(TAB / "image_night_check.csv", index=False, encoding="utf-8-sig", float_format="%.6g")
        N["night_check"] = {s: dict(n=len(g), fetched=int(g.fetched.sum()), stored_brightness_min=g.brightness_stored.min(),
                                    stored_brightness_max=g.brightness_stored.max(),
                                    recomputed_minus_stored_median=round(float((g.brightness_recomputed_from_thumb - g.brightness_stored).median()), 2),
                                    recomputed_minus_stored_maxabs=round(float((g.brightness_recomputed_from_thumb - g.brightness_stored).abs().max()), 2))
                            for s, g in nc.groupby("set")}
    except Exception as e:  # noqa: BLE001
        N["night_check"] = f"failed: {type(e).__name__}: {e}"

    # 6/7. example grids and figures
    example_grids(S)
    figures(S)
    (TAB / "image_numbers.json").write_text(json.dumps(N, indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o)),
                                            encoding="utf-8")
    print("n per group:", grp_n, "mismatch:", N["n_per_group_expected_mismatch"])
    print("format:", {k: v for k, v in N["format"].items() if k.startswith("n_")})


if __name__ == "__main__":
    main()
