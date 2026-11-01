"""Step 1b-check: are 360 'captured_at' hours trustworthy? (Many panos are stamped 22-01h.)
Samples up to 12 panos per (creator, local hour), downloads the 256-px thumbnail and measures mean brightness
(0-255) of the upper half (sky/buildings). Daylight images are bright regardless of the stamped hour.
Output: data/raw/metadata/capture_time_check_<date>.csv + per-hour summary."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import concurrent.futures as cf
import io
import sys
from datetime import date

import numpy as np
import pandas as pd
import requests
from PIL import Image

from common import RAW_META, env

S = requests.Session()
S.headers["Authorization"] = f"OAuth {env('MAPILLARY_TOKEN')}"
f = sorted(RAW_META.glob("mapillary_pano_*.parquet"))[-1] if len(sys.argv) < 2 else RAW_META / sys.argv[1]
m = pd.read_parquet(f)
m["hour"] = m.captured.dt.hour
top = m.creator.value_counts().index[:3]
smp = m[m.creator.isin(top)].sample(frac=1, random_state=0).groupby(["creator", "hour"]).head(12).copy()


def bright(iid):
    try:
        url = S.get(f"https://graph.mapillary.com/{iid}", params={"fields": "thumb_256_url"}, timeout=30).json()["thumb_256_url"]
        a = np.asarray(Image.open(io.BytesIO(requests.get(url, timeout=30).content)).convert("L"), dtype=float)
        return a[: a.shape[0] // 2].mean()
    except Exception:  # noqa: BLE001
        return np.nan


with cf.ThreadPoolExecutor(8) as ex:
    smp["brightness"] = list(ex.map(bright, smp.id))
smp[["id", "creator", "captured", "hour", "brightness"]].to_csv(RAW_META / f"capture_time_check_{date.today():%Y%m%d}.csv", index=False)
cnt = m[m.creator.isin(top)].groupby(["creator", "hour"]).size().rename("panos")
summ = smp.groupby(["creator", "hour"]).brightness.agg(["median", "min", "count"]).round(0).join(cnt)
pd.set_option("display.max_rows", 200)
print(summ.to_string())
