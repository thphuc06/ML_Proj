"""Step 3 (pilot): one Label Studio project per annotator (PILOT_<name>), same 150 crops, own shuffled order.
Blind by convention (Community edition has no roles): each person opens only their own project.
Each project gets a Local Files storage on crops/pilot (needed for /data/local-files serving; never synced -
tasks are imported explicitly). Instructions = guide v0. Tasks = pilot v2 (right crops, opaque item codes). Re-running skips projects that already have tasks.
Prerequisite: data/crops/pilot_v2 copied to /srv/sidewalk/data/crops/pilot_v2 on the server."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import re

import numpy as np
import pandas as pd

from common import DATA, ROOT
from ls_client import BASE, FILES_ROOT, projects, session

GUIDE = ROOT / "labeling" / "guide" / "annotation_guide_v0.md"
CONFIG = (ROOT / "labeling" / "label_studio" / "ls_label_config_v0.xml").read_text(encoding="utf-8")
NAMES = re.findall(r"^\s{2}(\w+):", (ROOT / "labeling" / "label_studio" / "annotators.yaml").read_text(encoding="utf-8"), flags=re.M)

try:
    import markdown
    instr = markdown.markdown(GUIDE.read_text(encoding="utf-8"), extensions=["tables"])
except ImportError:
    instr = "<pre style='white-space:pre-wrap'>" + GUIDE.read_text(encoding="utf-8") + "</pre>"

man = pd.read_csv(DATA / "manifest" / "pilot_v2.csv")
s = session()
have = projects(s)
for k, name in enumerate(NAMES):
    title = f"PILOT_{name}"
    p = have.get(title)
    if p and p.get("task_number"):
        print(title, "exists with", p["task_number"], "tasks - skipped")
        continue
    if not p:
        p = s.post(BASE + "/api/projects", json={
            "title": title, "description": f"Pilot gán nhãn vỉa hè – CHỈ {name} mở project này. 150 ảnh, guide v0.",
            "label_config": CONFIG, "expert_instruction": instr, "show_instruction": True, "show_skip_button": False,
            "enable_empty_annotation": False, "show_annotation_history": False, "maximum_annotations": 1,
            "sampling": "Sequential sampling", "color": "#2D6A9F"}).json()
        if "id" not in p:
            raise SystemExit(f"create {title} failed: {p}")
    st = s.post(BASE + "/api/storages/localfiles", json={
        "project": p["id"], "title": "crops_pilot_v2", "path": f"{FILES_ROOT}/crops/pilot_v2", "use_blob_urls": True})
    if st.status_code >= 300:
        raise SystemExit(f"storage for {title} failed: {st.status_code} {st.text[:300]}")
    order = man.sample(frac=1, random_state=1000 + k)
    tasks = [{"data": {"image": f"/data/local-files/?d=crops/{r.file}", "item": r.item}} for r in order.itertuples()]
    r = s.post(BASE + f"/api/projects/{p['id']}/import", json=tasks)
    print(title, "id", p["id"], "| import", r.status_code, r.json().get("task_count", r.text[:200]))
