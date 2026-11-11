"""Train enrichment labelling: one Label Studio project per annotator (MAIN2_<name>) with the crops of
data/manifest/train_extra_v1_assignment.csv (written by src/collection/23_collect_train_extra.py).
- Same interface (ls_label_config_v1.xml) and instructions (guide v1) as the MAIN_ projects.
- Separate projects, so the closed MAIN_ projects and 19_main_agreement.py are not touched.
- Tasks carry the image and the opaque item code only: no stratum, no score, no street. Private random order per project.
The crops must be on the server first, in /srv/sidewalk/data/crops/train_extra_v1 (see infra/README.md).
Default = dry run (prints what would be created). --apply creates the projects; projects that already hold tasks are skipped.
Usage: python src/labeling/25_ls_create_train_extra.py [--apply]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import markdown
import pandas as pd

from common import DATA, ROOT
from ls_client import BASE, FILES_ROOT, projects, session

APPLY = "--apply" in sys.argv
asg = pd.read_csv(DATA / "manifest" / "train_extra_v1_assignment.csv", dtype=str)
man = pd.read_csv(DATA / "manifest" / "train_extra_v1.csv", dtype=str)
assert set(asg.item) == set(man.item) and not asg.duplicated("item").any() and (asg.split == "train").all()
cfg = (ROOT / "labeling" / "label_studio" / "ls_label_config_v1.xml").read_text(encoding="utf-8")
instr = markdown.markdown((ROOT / "labeling" / "guide" / "annotation_guide_v1_draft.md").read_text(encoding="utf-8"), extensions=["tables"])
instr = instr.replace("PILOT_&lt;tên&gt;", "MAIN2_&lt;tên&gt;")
s = session()
have = projects(s)
print("APPLY" if APPLY else "dry run (nothing changes on the server)", "|", len(asg), "crops")
for k, (name, mine) in enumerate(asg.groupby("annotator")):
    title = f"MAIN2_{name}"
    p = have.get(title)
    if p and p.get("task_number"):
        print(title, "exists with", p["task_number"], "tasks - skipped")
        continue
    mine = mine.sample(frac=1, random_state=5000 + k)
    print(title, "|", len(mine), "tasks")
    if not APPLY:
        continue
    p = p or s.post(BASE + "/api/projects", json={
        "title": title, "description": f"Gán đợt 2 – CHỈ {name} mở project này. Hướng dẫn và giao diện giống MAIN_{name} (guide v1).",
        "label_config": cfg, "expert_instruction": instr, "show_instruction": True, "show_skip_button": False,
        "enable_empty_annotation": False, "show_annotation_history": False, "maximum_annotations": 1,
        "sampling": "Sequential sampling", "color": "#1F5A7A"}).json()
    s.post(BASE + "/api/storages/localfiles", json={"project": p["id"], "title": "crops_train_extra_v1", "path": f"{FILES_ROOT}/crops/train_extra_v1", "use_blob_urls": True})
    probe = s.get(BASE + f"/data/local-files/?d=crops/{mine.file.iloc[0]}")  # served only once a storage covers the folder
    if probe.status_code != 200:
        raise SystemExit(f"{title}: first image not served ({probe.status_code}); are the crops on the server? No task imported.")
    r = s.post(BASE + f"/api/projects/{p['id']}/import", json=[{"data": {"image": f"/data/local-files/?d=crops/{f}", "item": i}} for i, f in zip(mine.item, mine.file)])
    print("  -> id", p["id"], "| import", r.status_code, r.json().get("task_count"))
