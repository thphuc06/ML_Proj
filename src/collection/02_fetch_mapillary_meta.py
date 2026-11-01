"""Step 1b: metadata of every Mapillary 360-degree image in the study area (no image download).
The API rejects bboxes larger than about 0.001 deg in dense HCMC, so the area is scanned in 0.001-deg cells
with the server-side is_pano filter; a cell returning the 2000-row limit is split in 4.
Output: data/raw/metadata/mapillary_pano_<YYYYMMDD>.parquet (+ failed cells json)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import concurrent.futures as cf
import json
import time
from datetime import date

import pandas as pd
import requests

from common import BBOX, RAW_META, env

FIELDS = "id,is_pano,captured_at,compass_angle,computed_compass_angle,computed_geometry,sequence,creator,camera_type,width,height"
STEP = 0.001
S = requests.Session()
S.headers["Authorization"] = f"OAuth {env('MAPILLARY_TOKEN')}"


def query(x0, y0, x1, y1, depth=0):
    for attempt in range(5):
        try:
            d = S.get("https://graph.mapillary.com/images", timeout=90, params={
                "bbox": f"{x0:.6f},{y0:.6f},{x1:.6f},{y1:.6f}", "fields": FIELDS, "limit": 2000, "is_pano": "true"}).json()
        except Exception:  # noqa: BLE001
            time.sleep(3 * (attempt + 1))
            continue
        msg = d.get("error", {}).get("message", "")
        rows = d.get("data", [])
        if ("reduce" in msg or len(rows) >= 2000) and depth < 3:
            xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
            return [r for b in [(x0, y0, xm, ym), (xm, y0, x1, ym), (x0, ym, xm, y1), (xm, ym, x1, y1)]
                    for r in query(*b, depth=depth + 1)]
        if msg:
            time.sleep(3 * (attempt + 1))
            continue
        return rows
    return [{"_failed_cell": [x0, y0, x1, y1]}]


s, w, n, e = BBOX
nx, ny = round((e - w) / STEP), round((n - s) / STEP)
cells = [(w + i * STEP, s + j * STEP, w + (i + 1) * STEP, s + (j + 1) * STEP) for i in range(nx) for j in range(ny)]
t0, rows, failed = time.time(), [], []
with cf.ThreadPoolExecutor(8) as ex:
    for k, res in enumerate(ex.map(lambda c: query(*c), cells), 1):
        for r in res:
            if "_failed_cell" in r:
                failed.append(r["_failed_cell"])
                continue
            lon, lat = ((r.pop("computed_geometry", None) or {}).get("coordinates") or [None, None])[:2]
            rows.append({**r, "lon": lon, "lat": lat, "creator": (r.pop("creator", None) or {}).get("username")})
        if k % 500 == 0:
            print(f"{k}/{len(cells)} cells | {len(rows)} panos | {time.time() - t0:.0f}s", flush=True)

df = pd.DataFrame(rows).drop_duplicates("id")
df["captured"] = pd.to_datetime(df.captured_at, unit="ms", utc=True).dt.tz_convert("Asia/Ho_Chi_Minh")
out = RAW_META / f"mapillary_pano_{date.today():%Y%m%d}.parquet"
df.to_parquet(out, index=False)
(RAW_META / f"failed_cells_{date.today():%Y%m%d}.json").write_text(json.dumps(failed))
print(f"{len(df)} panos -> {out.name} | failed cells {len(failed)} | {time.time() - t0:.0f}s")
