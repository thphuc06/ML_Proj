"""Step 3b: move the MAIN_<name> projects to the v1 interface (ls_label_config_v1.xml + guide v1) and remap reasons
already given under v0. Only the `reason` choices differ between v0 and v1; label, obstacles, difficult and note are equal.
  v0 "Không thấy vỉa hè gần" and "Phía này không có vỉa hè" -> v1 "Không thấy vỉa hè" (merged, collection_log 2026-11-01)
  v0 "Ảnh mờ / tối / khung lệch" -> "Ảnh mờ / tối / cháy sáng"; "Phần quyết định bị che" -> "Bị che"; "Lý do khác" unchanged
Every run first saves a full JSON export of each MAIN project to data/labels/raw/main_backup_<time>/ (gitignored: it
holds account emails). Default = dry run (report only). With --apply, per project with old reasons:
  1. temporary config = v1 + the old reason values (no hotkeys), so Label Studio accepts it with the old annotations
  2. PATCH each annotation that uses an old reason (only the reason value changes)
  3. final config = v1 and the v1 guide as instructions; then re-export and check that no old reason is left
PILOT_* projects are never touched (their v0 labels are the pilot record). Ask annotators not to submit while it runs.
Usage: python src/labeling/18_ls_update_main_v1.py [--apply]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import copy
import json
from datetime import datetime

import markdown

from common import DATA, ROOT
from ls_client import BASE, projects, session

APPLY = "--apply" in sys.argv
REMAP = {"Không thấy vỉa hè gần": "Không thấy vỉa hè", "Phía này không có vỉa hè": "Không thấy vỉa hè",
         "Ảnh mờ / tối / khung lệch": "Ảnh mờ / tối / cháy sáng", "Phần quyết định bị che": "Bị che"}
V1 = (ROOT / "labeling" / "label_studio" / "ls_label_config_v1.xml").read_text(encoding="utf-8")
ANCHOR = '<Choice value="Lý do khác" hotkey="j"/>'
assert ANCHOR in V1 and all(v in V1 for v in REMAP.values()), "ls_label_config_v1.xml changed: update REMAP/ANCHOR"
UNION = V1.replace(ANCHOR, ANCHOR + "".join(f'\n        <Choice value="{v}"/>' for v in REMAP))
INSTR = markdown.markdown((ROOT / "labeling" / "guide" / "annotation_guide_v1_draft.md").read_text(encoding="utf-8"), extensions=["tables"])
INSTR = INSTR.replace("PILOT_&lt;tên&gt;", "MAIN_&lt;tên&gt;")
BACKUP = DATA / "labels" / "raw" / f"main_backup_{datetime.now():%Y%m%d_%H%M}"
BACKUP.mkdir(parents=True, exist_ok=True)


def export(s, pid):
    r = s.get(BASE + f"/api/projects/{pid}/export", params={"exportType": "JSON"}, timeout=300)
    r.raise_for_status()
    return r.json()


def remap(result):
    """Copy of an annotation result with old reason values replaced; None when nothing changes."""
    new, hit = copy.deepcopy(result), False
    for reg in new:
        if reg.get("from_name") == "reason":
            ch = reg["value"]["choices"]
            reg["value"]["choices"] = [REMAP.get(c, c) for c in ch]
            hit |= reg["value"]["choices"] != ch
    return new if hit else None


def reasons(tasks):
    out = {}
    for t in tasks:
        for a in t.get("annotations", []):
            for reg in a["result"]:
                if reg.get("from_name") == "reason":
                    for c in reg["value"]["choices"]:
                        out[c] = out.get(c, 0) + 1
    return out


def patch(s, url, body):
    r = s.patch(BASE + url, json=body, timeout=60)
    if not r.ok:
        raise SystemExit(f"PATCH {url} failed {r.status_code}: {r.text[:400]}")


s = session()
main = {t: p for t, p in projects(s).items() if t.startswith("MAIN_")}
print("dry run (nothing changes on the server)" if not APPLY else "APPLY", "| backup ->", BACKUP)
for title, p in sorted(main.items()):
    tasks = export(s, p["id"])
    (BACKUP / f"{title}.json").write_text(json.dumps(tasks, ensure_ascii=False), encoding="utf-8")
    cfg = s.get(BASE + f"/api/projects/{p['id']}").json()["label_config"]
    todo = [(a["id"], new) for t in tasks for a in t.get("annotations", []) if (new := remap(a["result"]))]
    n_ann = sum(len(t.get("annotations", [])) for t in tasks)
    state = "v1" if cfg.strip() == V1.strip() else "v0" if "Phía này không có vỉa hè" in cfg else "other"
    print(f"{title}: config {state} | tasks {len(tasks)} | annotations {n_ann} | reasons {reasons(tasks)} | to remap {len(todo)}")
    if not APPLY:
        continue
    if todo:
        patch(s, f"/api/projects/{p['id']}", {"label_config": UNION})
        for aid, new in todo:
            patch(s, f"/api/annotations/{aid}", {"result": new})
    patch(s, f"/api/projects/{p['id']}", {"label_config": V1, "expert_instruction": INSTR, "show_instruction": True})
    left = {c: n for c, n in reasons(export(s, p["id"])).items() if c in REMAP}
    print(f"  -> config v1, remapped {len(todo)}, old reasons left {left or 'none'}")
