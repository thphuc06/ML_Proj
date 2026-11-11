"""Step 3c (main labelling done): agreement, label counts and the adjudication list for the MAIN_<name> projects.
Reads a raw export folder (default: the newest data/labels/raw/main_export_*; --fresh pulls a new read-only export first).
- one row per (item, annotator); a task saved twice keeps the latest annotation (reported)
- reasons from the v0 interface are mapped to the v1 names (same map as 18_ls_update_main_v1.py)
- Cohen's kappa for the test pair, the val pair and the train cross-check pairs (3-way and binary)
- items to adjudicate: any double-labelled item whose two labels differ
- provisional label per item: the agreed label, or the single label (train_single); disagreements stay open
Outputs in data/labels/main_report/: main_labels.csv, main_items.csv, main_adjudicate.csv, main_report.md
Final labels: data/labels/main_labels_v1.csv = main items (adjudicated) + the 150 pilot items re-reviewed under guide v1
(data/labels/pilot_report/pilot_adjudication_proposal.csv); column `phase` tells them apart.
Usage: python src/labeling/19_main_agreement.py [--fresh]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import json
from datetime import datetime

import numpy as np
import pandas as pd

from common import DATA

MAP = {"0 – Còn lối đi": "0", "1 – Bị chặn": "1", "Không đủ thông tin": "I"}
REASON_V1 = {"Không thấy vỉa hè gần": "Không thấy vỉa hè", "Phía này không có vỉa hè": "Không thấy vỉa hè",
             "Ảnh mờ / tối / khung lệch": "Ảnh mờ / tối / cháy sáng", "Phần quyết định bị che": "Bị che"}
RAW, REP = DATA / "labels" / "raw", DATA / "labels" / "main_report"
REP.mkdir(parents=True, exist_ok=True)

if "--fresh" in sys.argv:
    from ls_client import BASE, projects, session
    src = RAW / f"main_export_{datetime.now():%Y%m%d_%H%M}"
    src.mkdir(parents=True, exist_ok=True)
    s = session()
    for title, p in projects(s).items():
        if title.startswith("MAIN_"):
            r = s.get(BASE + f"/api/projects/{p['id']}/export", params={"exportType": "JSON"}, timeout=300)
            r.raise_for_status()
            (src / f"{title}.json").write_text(json.dumps(r.json(), ensure_ascii=False), encoding="utf-8")
else:
    src = sorted(RAW.glob("main_export_*"))[-1]


def cohen(a, b):
    a, b = np.asarray(a), np.asarray(b)
    po = np.mean(a == b)
    pe = sum(np.mean(a == c) * np.mean(b == c) for c in set(a) | set(b))
    return np.nan if pe == 1 else (po - pe) / (1 - pe)


rows, dup = [], 0
for f in sorted(src.glob("MAIN_*.json")):
    for t in json.loads(f.read_text(encoding="utf-8")):
        anns = sorted([a for a in t.get("annotations", []) if not a.get("was_cancelled")], key=lambda a: a["updated_at"])
        dup += max(0, len(anns) - 1)
        if not anns:
            continue
        a = anns[-1]
        res = {r["from_name"]: r["value"] for r in a["result"]}
        ch = lambda k: res.get(k, {}).get("choices", [])  # noqa: E731
        rows.append({"item": t["data"]["item"], "annotator": f.stem[5:], "label": MAP.get((ch("label") or [None])[0]),
                     "reason": "|".join(REASON_V1.get(c, c) for c in ch("reason")), "obstacles": "|".join(ch("obstacles")),
                     "difficult": bool(ch("difficult")), "note": " ".join(res.get("note", {}).get("text", [])),
                     "seconds": a.get("lead_time"), "updated_at": a["updated_at"]})
lab = pd.DataFrame(rows)
asg = pd.read_csv(DATA / "manifest" / "main_v1_assignment.csv")
lab = asg.merge(lab, on=["item", "annotator"], how="left")
missing = lab.label.isna().sum()
lab.to_csv(REP / "main_labels.csv", index=False, encoding="utf-8-sig")

# one row per item: labels of the (up to two) annotators
lab["slot"] = lab.groupby("item").cumcount()
W = lab.pivot(index="item", columns="slot", values=["annotator", "label", "reason", "obstacles", "role"])
W.columns = [f"{a}{b + 1}" for a, b in W.columns]
items = W.reset_index().merge(pd.read_csv(DATA / "manifest" / "main_v1.csv")[["item", "split", "street_id"]], on="item")
double = items.label2.notna()
items["status"] = np.where(~double, "single", np.where(items.label1 == items.label2, "agreed", "disagree"))
items["label_prov"] = np.where(items.status == "disagree", "?", items.label1)
# adjudication: proposal (Claude, by eye, guide v1) unless Phuc wrote a label in column `phuc`
ADJ = REP / "adjudication_proposal.csv"
if ADJ.exists():
    a = pd.read_csv(ADJ, dtype=str).fillna("")
    a["final"] = a.phuc.where(a.phuc.isin(["0", "1", "I"]), a.proposed)
    items = items.merge(a[["item", "final"]], on="item", how="left")
    items["label_final"] = items.final.fillna(items.label_prov)
    items = items.drop(columns="final")
    phuc = set(a.item[a.phuc.isin(["0", "1", "I"])])
    items["source"] = np.select([items.item.isin(phuc), items.status.eq("disagree")], ["adjudicated_phuc", "adjudicated_proposal"],
                                items.status)
items.to_csv(REP / "main_items.csv", index=False, encoding="utf-8-sig")
if "label_final" in items and (items.label_final != "?").all():
    # final label table (phase 1): one row per item; insufficient reason kept when both/the only annotator agree on it
    rs = lab.groupby("item").reason.agg(lambda x: x.iloc[0] if x.nunique() == 1 else "")
    fin = items[["item", "split", "street_id", "label_final", "source"]].rename(columns={"label_final": "label"})
    fin["reason"] = fin.item.map(rs).where(fin.label == "I", "")
    fin.insert(1, "phase", "main")
    fin.insert(2, "file", "main/" + fin.item + ".jpg")
    # pilot items (train streets, labelled under guide v0): every item re-reviewed under guide v1, Phuc's label wins
    PIL = DATA / "labels" / "pilot_report" / "pilot_adjudication_proposal.csv"
    if PIL.exists():
        pa = pd.read_csv(PIL, dtype=str).fillna("")
        own = pa.phuc.isin(["0", "1", "I"])
        pil = pd.DataFrame({"item": pa["item"], "phase": "pilot", "file": "pilot_v2/" + pa["item"] + ".jpg",
                            "split": pa.split, "street_id": pa.street_id, "label": pa.phuc.where(own, pa.proposed),
                            "source": np.where(own, "pilot_review_phuc", "pilot_review_proposal"), "reason": ""})
        fin = pd.concat([fin, pil], ignore_index=True)
    assert not fin.item.duplicated().any()
    fin.to_csv(DATA / "labels" / "main_labels_v1.csv", index=False, encoding="utf-8-sig")
adj = items[items.status == "disagree"].copy()
adj["pair"] = adj.label1 + "/" + adj.label2
adj.sort_values(["split", "pair", "street_id"]).to_csv(REP / "main_adjudicate.csv", index=False, encoding="utf-8-sig")

out = [f"# Main labelling report ({datetime.now():%d/%m/%Y})", "",
       f"Export: `{src.relative_to(DATA.parent).as_posix()}` (gitignored). Annotations: {len(lab) - missing}/{len(lab)} assigned slots,"
       f" {missing} missing, {dup} task(s) saved twice (latest kept).", "", "## Per annotator", "",
       lab.groupby("annotator").agg(n=("item", "size"), share0=("label", lambda x: (x == "0").mean()),
                                    share1=("label", lambda x: (x == "1").mean()), shareI=("label", lambda x: (x == "I").mean()),
                                    median_s=("seconds", "median"), under_2s=("seconds", lambda x: (x < 2).mean()),
                                    difficult=("difficult", "mean"), notes=("note", lambda x: (x.fillna("") != "").sum())).round(2).to_markdown(),
       "", "## Agreement on double-labelled items", "",
       "| group | pair | n | raw agree | κ 3-way | κ binary | n binary |", "|---|---|---|---|---|---|---|"]
D = items[double].copy()
D["grp"] = D.split.where(D.split != "train", "train (cross 15%)")
for (g, pair), d in D.groupby(["grp", D.annotator1 + "–" + D.annotator2]):
    if len(d) < 10:
        continue
    b = d[d.label1.isin(["0", "1"]) & d.label2.isin(["0", "1"])]
    out.append(f"| {g} | {pair} | {len(d)} | {np.mean(d.label1 == d.label2):.0%} | {cohen(d.label1, d.label2):.2f} | {cohen(b.label1, b.label2):.2f} | {len(b)} |")
for g, d in D.groupby("grp"):
    b = d[d.label1.isin(["0", "1"]) & d.label2.isin(["0", "1"])]
    out.append(f"| **{g}, all** | | {len(d)} | {np.mean(d.label1 == d.label2):.0%} | **{cohen(d.label1, d.label2):.2f}** | {cohen(b.label1, b.label2):.2f} | {len(b)} |")
conf = pd.crosstab(D.grp, D.label1.where(D.label1 <= D.label2, D.label2) + "/" + D.label2.where(D.label1 <= D.label2, D.label1))
out += ["", "## Label pairs on double-labelled items (unordered)", "", conf.to_markdown(),
        "", "## Provisional label per item (disagreements open)", "",
        pd.crosstab([items.split, items.status], items.label_prov, margins=True).to_markdown(),
        "", "## Blocked (1) per split, before adjudication", "",
        "| split | items | agreed or single 1 | open with a 1 vote | 1 if every open item went to 1 |", "|---|---|---|---|---|"]
for sp, d in items.groupby("split"):
    has1 = d.status.eq("disagree") & (d.label1.eq("1") | d.label2.eq("1"))
    out.append(f"| {sp} | {len(d)} | {(d.label_prov == '1').sum()} | {has1.sum()} | {(d.label_prov == '1').sum() + has1.sum()} |")
if "label_final" in items:
    n_phuc = (a.phuc.isin(["0", "1", "I"])).sum()
    out += ["", f"## After adjudication ({len(a)} items: proposal by eye, {n_phuc} changed by Phuc)", "",
            pd.crosstab(items.split, items.label_final, margins=True).to_markdown(), "",
            "| split | blocked | usable (0/1) | blocked share of usable |", "|---|---|---|---|"]
    for sp, d in items.groupby("split"):
        u = d.label_final.isin(["0", "1"]).sum()
        out.append(f"| {sp} | {(d.label_final == '1').sum()} | {u} | {(d.label_final == '1').sum() / u:.1%} |")
L = lab.dropna(subset=["label"])
out += ["", "## Insufficient reasons (v0 names mapped to v1)", "", L[L.label == "I"].reason.replace("", "(missing)").value_counts().to_markdown(),
        "", "## Blocked labels without an obstacle tag", "",
        L[L.label == "1"].groupby("annotator").obstacles.apply(lambda x: f"{(x == '').sum()}/{len(x)}").to_markdown(),
        "", "## Labels by street (all annotations)", "", pd.crosstab([L.split, L.street_id], L.label, normalize="index").round(2).to_markdown()]
(REP / "main_report.md").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
print("\nto adjudicate:", len(adj), "->", REP / "main_adjudicate.csv")
