"""EDA prerequisite: rebuild the main_v1 / pilot_v2 crops that are missing on this machine (the originals live on the
labelling server). Same projection as the dataset crop (enrich.crop_at_yaw with the manifest yaw). A rebuilt crop
differs from the server copy only by JPEG re-encoding (docs/collection_log.md 2026-11-11: 1.35-1.5 grey levels).
No label is read. Needs MAPILLARY_TOKEN in .env. Output: data/crops/<file> (not in git)."""
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, enrich.py

import pandas as pd
from PIL import Image

from common import DATA
from enrich import crop_at_yaw, fetch_pano

M = pd.concat([pd.read_csv(DATA / "manifest" / f, encoding="utf-8-sig") for f in ("main_v1.csv", "pilot_v2.csv")])
todo = M[[not (DATA / "crops" / f).exists() for f in M.file]]
print(f"{len(M)} manifest rows, {len(todo)} crops missing", flush=True)


def build(r):
    equi = fetch_pano(r.parent_pano_id)
    if equi is None:
        return r.item
    out = DATA / "crops" / r.file
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(crop_at_yaw(equi, r.yaw)).save(out, quality=90)
    return None


with ThreadPoolExecutor(8) as ex:
    failed = [x for x in ex.map(build, todo.itertuples()) if x]
print(f"rebuilt {len(todo) - len(failed)}, failed {len(failed)}: {failed}")
