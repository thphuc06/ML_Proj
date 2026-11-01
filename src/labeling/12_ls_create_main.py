"""Step 3 (main labelling): assignment + one Label Studio project per annotator (MAIN_<name>).
- test: every item labelled blind by the fixed TEST pair; val: by the fixed VAL pair
- train: one annotator per item, 15% of items get a second, different annotator (cross-check)
- train slots fill each person up to an equal total; each project mixes splits/streets in a private random order
Assignment saved to data/manifest/main_v1_assignment.csv (item, annotator, role). Re-running skips projects with tasks."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import re

import numpy as np
import pandas as pd

from common import DATA, ROOT
from ls_client import BASE, FILES_ROOT, projects, session

TEST_PAIR, VAL_PAIR, CROSS = ["Hoc", "Loan"], ["Minh", "Khai"], 0.15
NAMES = re.findall(r"^\s{2}(\w+):", (ROOT / "labeling" / "label_studio" / "annotators.yaml").read_text(encoding="utf-8"), flags=re.M)
rng = np.random.RandomState(20261024)
man = pd.read_csv(DATA / "manifest" / "main_v1.csv")

rows = [{"item": i, "annotator": a, "role": "test_double"} for i in man[man.split == "test"].item for a in TEST_PAIR]
rows += [{"item": i, "annotator": a, "role": "val_double"} for i in man[man.split == "val"].item for a in VAL_PAIR]
train = man[man.split == "train"].item.sample(frac=1, random_state=rng).tolist()
cross = set(train[: int(round(CROSS * len(train)))])
load = pd.Series(0, index=NAMES)
for r in rows:
    load[r["annotator"]] += 1
total = load.sum() + len(train) + len(cross)
target = pd.Series(total // len(NAMES), index=NAMES)
target.iloc[: total - target.sum()] += 1
cap = target - load                      # train slots each person still takes
assert (cap >= 0).all(), cap
slots = [(i, "train_cross_2nd" if k else ("train_cross_1st" if i in cross else "train_single")) for i in train for k in range(2 if i in cross else 1)]
order = rng.permutation(len(slots))
owner_of = {}
for j in order:  # fill people with the most remaining capacity; a cross item's two slots go to different people
    item, role = slots[j]
    cand = cap[cap > 0].sort_values(ascending=False)
    a = next(n for n in cand.index if owner_of.get(item) != n)
    owner_of.setdefault(item, a)
    cap[a] -= 1
    rows.append({"item": item, "annotator": a, "role": role})
asg = pd.DataFrame(rows).merge(man[["item", "file", "split", "street_id"]], on="item")
asg.to_csv(DATA / "manifest" / "main_v1_assignment.csv", index=False, encoding="utf-8-sig")
print(asg.pivot_table(index="annotator", columns="role", values="item", aggfunc="size", fill_value=0).assign(total=lambda d: d.sum(1)).to_string())
assert not asg.duplicated(["item", "annotator"]).any()

cfg = (ROOT / "labeling" / "label_studio" / "ls_label_config_v1.xml").read_text(encoding="utf-8")
import markdown  # noqa: E402
instr = markdown.markdown((ROOT / "labeling" / "guide" / "annotation_guide_v1_draft.md").read_text(encoding="utf-8"), extensions=["tables"])
instr = instr.replace("PILOT_&lt;tên&gt;", "MAIN_&lt;tên&gt;").replace("<code>PILOT_&lt;tên&gt;</code>", "<code>MAIN_&lt;tên&gt;</code>")
s = session()
have = projects(s)
for k, name in enumerate(NAMES):
    title = f"MAIN_{name}"
    p = have.get(title)
    if p and p.get("task_number"):
        print(title, "exists with", p["task_number"], "tasks - skipped")
        continue
    p = p or s.post(BASE + "/api/projects", json={
        "title": title, "description": f"Gán chính thức – CHỈ {name} mở project này. Bắt đầu SAU buổi họp pilot (guide v1).",
        "label_config": cfg, "expert_instruction": instr, "show_instruction": True, "show_skip_button": False,
        "enable_empty_annotation": False, "show_annotation_history": False, "maximum_annotations": 1,
        "sampling": "Sequential sampling", "color": "#1F7A4D"}).json()
    s.post(BASE + "/api/storages/localfiles", json={"project": p["id"], "title": "crops_main", "path": f"{FILES_ROOT}/crops/main", "use_blob_urls": True})
    mine = asg[asg.annotator == name].sample(frac=1, random_state=3000 + k)
    r = s.post(BASE + f"/api/projects/{p['id']}/import", json=[{"data": {"image": f"/data/local-files/?d=crops/{f}", "item": i}} for i, f in zip(mine.item, mine.file)])
    print(title, "id", p["id"], "| import", r.status_code, r.json().get("task_count"))
