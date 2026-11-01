"""Step 1c: rank candidate streets by usable Mapillary 360 coverage and describe their context.

Street = OSM ways with the same normalised name whose geometries are within 40 m (joins dual carriageways and
small gaps; far-apart same-name streets stay separate). Alleys (Hem/Kiet/Ngo) are excluded (usually no sidewalk).
Pano -> street: within 20 m of a street segment AND travel bearing within 30 deg of the segment axis
(so panos on a cross street at an intersection are not assigned). Travel bearing = bearing between the
images 2 before / 2 after in the same sequence (helmet cameras turn with the rider's head, compass alone is unreliable).
Centerline length = area of the 20 m buffer / 40 m (dual carriageways counted once).
Positions: matched panos thinned greedily to >= 25 m apart; passes = distinct capture days within 15 m of a position.
est_usable_crops = sum(min(passes, 2)) * 2 sides * 0.46 (usable share of crops from an earlier trial run).
Context (description only): shops/food within 30 m per km, markets and schools within 150 m.
Output: data/streets/street_candidates_v1.csv (+ printed summary)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import json
import re
import sys
from collections import defaultdict

import numpy as np
import pandas as pd
from shapely import STRtree
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from common import DATA, RAW_META, RAW_OSM, axis_diff, bearing_xy, to_xy

OUT = DATA / "streets"
OUT.mkdir(exist_ok=True)
MATCH_M, AXIS_DEG, THIN_M, PASS_M, USABLE = 20, 30, 25, 15, 0.46


def norm_name(n):
    n = re.sub(r"^(Đường|Duong|Phố)\s+", "", n.strip(), flags=re.I)
    return re.sub(r"\s+", " ", n)


# ---- streets
ways = [w for w in json.load(open(RAW_OSM / "roads.json", encoding="utf-8"))["elements"]
        if not re.match(r"^(Hẻm|Kiệt|Ngõ|Ngách)\b", w["tags"]["name"], flags=re.I)]
by_name = defaultdict(list)
for w in ways:
    w["line"] = LineString([to_xy(p["lon"], p["lat"]) for p in w["geometry"]])
    by_name[norm_name(w["tags"]["name"])].append(w)

streets = []
for name, ws in by_name.items():
    parent = list(range(len(ws)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    tree = STRtree([w["line"] for w in ws])
    for i, w in enumerate(ws):
        for j in tree.query(w["line"], predicate="dwithin", distance=40):
            parent[find(i)] = find(int(j))
    comps = defaultdict(list)
    for i in range(len(ws)):
        comps[find(i)].append(ws[i])
    for k, cw in enumerate(sorted(comps.values(), key=lambda c: -sum(w["line"].length for w in c))):
        length = sum(w["line"].length for w in cw)
        oneway = sum(w["line"].length for w in cw if w["tags"].get("oneway") == "yes") / length
        hw = pd.Series({w["tags"]["highway"]: 0.0 for w in cw})
        for w in cw:
            hw[w["tags"]["highway"]] += w["line"].length
        geom = unary_union([w["line"] for w in cw])
        streets.append({"street_id": f"{name}#{k}" if len(comps) > 1 else name, "name": name, "geom": geom,
                        "ways": cw, "way_len_m": length, "oneway_share": oneway, "highway": hw.idxmax()})
print("streets (name components, alleys excluded):", len(streets))

# ---- segments index for matching
segs, seg_street, seg_axis = [], [], []
for si, s in enumerate(streets):
    for w in s["ways"]:
        c = list(w["line"].coords)
        for a, b in zip(c[:-1], c[1:]):
            if a != b:
                segs.append(LineString([a, b]))
                seg_street.append(si)
                seg_axis.append(bearing_xy(*a, *b))
seg_tree = STRtree(segs)

# ---- panos + travel bearing
meta_file = sorted(RAW_META.glob("mapillary_pano_*.parquet"))[-1] if len(sys.argv) < 2 else RAW_META / sys.argv[1]
m = pd.read_parquet(meta_file).dropna(subset=["lon", "lat"]).sort_values(["sequence", "captured_at"]).reset_index(drop=True)
m["x"], m["y"] = to_xy(m.lon.values, m.lat.values)
tb = np.full(len(m), np.nan)
for _, idx in m.groupby("sequence").indices.items():
    xs, ys = m.x.values[idx], m.y.values[idx]
    for p, i in enumerate(idx):
        a, b = max(0, p - 2), min(len(idx) - 1, p + 2)
        if a != b and np.hypot(xs[b] - xs[a], ys[b] - ys[a]) > 3:
            tb[i] = bearing_xy(xs[a], ys[a], xs[b], ys[b])
m["travel_bearing"] = tb
m["day"] = m.captured.dt.date
m["hour"] = m.captured.dt.hour
print(f"panos: {len(m)} from {meta_file.name} | with travel bearing: {np.isfinite(tb).mean():.1%}")

# ---- match pano -> street
street_of = np.full(len(m), -1)
dist_of = np.full(len(m), np.nan)
pts = [Point(x, y) for x, y in zip(m.x.values, m.y.values)]
pi, sj = seg_tree.query(pts, predicate="dwithin", distance=MATCH_M)
best = {}
for i, j in zip(pi, sj):
    if not np.isfinite(tb[i]) or axis_diff(tb[i], seg_axis[j]) > AXIS_DEG:
        continue
    d = segs[j].distance(pts[i])
    if i not in best or d < best[i][0]:
        best[i] = (d, seg_street[j])
for i, (d, si) in best.items():
    street_of[i], dist_of[i] = si, d
m["street_idx"], m["dist_m"] = street_of, dist_of
mm = m[m.street_idx >= 0]
print(f"matched to a street: {len(mm)} ({len(mm) / len(m):.1%})")
mm[["id", "sequence", "captured_at", "lon", "lat", "travel_bearing", "street_idx", "dist_m"]].assign(
    street_id=[streets[i]["street_id"] for i in mm.street_idx]).to_parquet(OUT / "pano_street_match_v1.parquet", index=False)

# ---- POIs
pois = json.load(open(RAW_OSM / "pois.json", encoding="utf-8"))["elements"]
P = defaultdict(list)
for e in pois:
    lon, lat = (e["lon"], e["lat"]) if "lon" in e else (e.get("center", {}).get("lon"), e.get("center", {}).get("lat"))
    if lon is None:
        continue
    a = e["tags"].get("amenity")
    kind = "market" if a == "marketplace" else "school" if a in ("school", "kindergarten") else "commerce"
    P[kind].append((Point(*to_xy(lon, lat)), e["tags"].get("name", "")))
ptree = {k: STRtree([p for p, _ in v]) for k, v in P.items()}


def near(kind, geom, d):
    return [P[kind][i][1] for i in ptree[kind].query(geom, predicate="dwithin", distance=d)]


# ---- per-street metrics
rows = []
for si, g in mm.groupby("street_idx"):
    s = streets[si]
    g = g.sort_values("captured_at")
    xy = g[["x", "y"]].values
    kept = []
    for k in range(len(g)):
        if all(np.hypot(*(xy[k] - xy[q])) >= THIN_M for q in kept):
            kept.append(k)
    passes = [g.day.values[np.hypot(*(xy - xy[k]).T) <= PASS_M].tolist() for k in kept]
    passes = [len(set(p)) for p in passes]
    center_len = s["geom"].buffer(20).area / 40  # parallel carriageways < 40 m apart overlap -> counted once
    span = 0.0
    if len(kept) > 1:
        kx = xy[kept]
        span = float(max(np.hypot(*(kx - kx[q]).T).max() for q in range(len(kx))))
    commerce = len(near("commerce", s["geom"], 30))
    rows.append({
        "street_id": s["street_id"], "highway": s["highway"], "centerline_km": round(center_len / 1000, 2),
        "covered_span_km": round(span / 1000, 2), "positions_25m": len(kept),
        "coverage_ratio": round(min(1, len(kept) * THIN_M / center_len), 2),
        "median_passes": float(np.median(passes)), "panos_matched": len(g),
        "est_usable_crops": int(sum(min(p, 2) for p in passes) * 2 * USABLE),
        "n_days": g.day.nunique(), "years": ",".join(sorted({str(d.year) for d in g.day})),
        "creators": ",".join(g.creator.value_counts().index[:2]),
        "share_6_18h": round(g.hour.between(6, 17).mean(), 2),
        "commerce_per_km": round(commerce / max(center_len / 1000, 0.1)),
        "markets": "; ".join(sorted({n for n in near("market", s["geom"], 150) if n}))[:120],
        "n_schools_150m": len(near("school", s["geom"], 150)),
        "schools": "; ".join(sorted({n for n in near("school", s["geom"], 150) if n}))[:120],
        "lon": round(float(g.lon.median()), 5), "lat": round(float(g.lat.median()), 5),
    })
df = pd.DataFrame(rows).sort_values("est_usable_crops", ascending=False)
df.to_csv(OUT / "street_candidates_v1.csv", index=False, encoding="utf-8-sig")
print("streets with >= 1 matched pano:", len(df), "| >= 150 est. usable crops:", int((df.est_usable_crops >= 150).sum()))
pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 40)
print(df.drop(columns=["markets", "schools", "lon", "lat", "creators"]).head(45).to_string(index=False))
