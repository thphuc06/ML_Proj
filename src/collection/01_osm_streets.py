"""Step 1a: OSM roads + context POIs for the study area via Overpass.
Roads: named primary/secondary/tertiary/unclassified/residential ways (pedestrian streets excluded).
POIs: shops, food/drink, markets, schools (used only to describe candidate streets, never as model features).
Output: data/raw/osm/roads.json, data/raw/osm/pois.json (raw Overpass responses, never edited)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import json
import time

import requests

from common import BBOX, RAW_OSM

URL = "https://overpass-api.de/api/interpreter"
B = ",".join(map(str, BBOX))
QUERIES = {
    "roads": f"""[out:json][timeout:300];
way["highway"~"^(primary|secondary|tertiary|unclassified|residential)$"]["name"]({B});
out body geom;""",
    "pois": f"""[out:json][timeout:300];
(
  nwr["shop"]({B});
  nwr["amenity"~"^(restaurant|cafe|fast_food|bar|marketplace|school|kindergarten|college|university)$"]({B});
);
out center tags;""",
}

for name, q in QUERIES.items():
    for attempt in range(4):
        r = requests.post(URL, data={"data": q}, timeout=400, headers={"User-Agent": "hcmus-sidewalk-study/1.0"})
        if r.ok:
            break
        print(name, "HTTP", r.status_code, "- retrying")
        time.sleep(30 * (attempt + 1))
    r.raise_for_status()
    d = r.json()
    (RAW_OSM / f"{name}.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    print(name, len(d["elements"]), "elements | osm timestamp", d.get("osm3s", {}).get("timestamp_osm_base"))
