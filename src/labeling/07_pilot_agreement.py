"""Step 3 (pilot analysis): export PILOT_* projects -> raw labels, agreement and timing for the pilot meeting.
- labels: 0 / 1 / I (insufficient) per annotator; raw export saved untouched in data/labels/raw/
- Cohen's kappa per annotator pair on the 3-way label (0/1/I) and on the binary label (items both called 0/1)
- Fleiss' kappa (3-way) over items labelled by every annotator who finished
- seconds per image (Label Studio lead_time), insufficient share by side (L vs R), reasons
- disagreement sheet: items without a clear majority, for the adjudication meeting
Usage: python 07_pilot_agreement.py [min_done=150]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import itertools
import json
import sys
from datetime import datetime

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from common import DATA
from ls_client import BASE, projects, session

MIN_DONE = int(sys.argv[1]) if len(sys.argv) > 1 else 150
MAP = {"0 – Còn lối đi": "0", "1 – Bị chặn": "1", "Không đủ thông tin": "I"}
RAW, REP = DATA / "labels" / "raw", DATA / "labels" / "pilot_report"
RAW.mkdir(parents=True, exist_ok=True)
REP.mkdir(parents=True, exist_ok=True)


def cohen(a, b):
    cats = sorted(set(a) | set(b))
    po = np.mean(np.array(a) == np.array(b))
    pe = sum(np.mean(np.array(a) == c) * np.mean(np.array(b) == c) for c in cats)
    return np.nan if pe == 1 else (po - pe) / (1 - pe)


def fleiss(table):  # items x categories counts, equal raters per item
    n = table.sum(1)[0]
    p = table.sum(0) / table.sum()
    P = ((table ** 2).sum(1) - n) / (n * (n - 1))
    pe = (p ** 2).sum()
    return (P.mean() - pe) / (1 - pe)


s = session()
stamp = datetime.now().strftime("%Y%m%d_%H%M")
rows = []
for title, p in projects(s).items():
    if not title.startswith("PILOT_"):
        continue
    ex = s.get(BASE + f"/api/projects/{p['id']}/export?exportType=JSON").json()
    (RAW / f"{title}_{stamp}.json").write_text(json.dumps(ex, ensure_ascii=False), encoding="utf-8")
    for t in ex:
        for a in t.get("annotations", []):
            if a.get("was_cancelled"):
                continue
            res = {r["from_name"]: r["value"] for r in a["result"]}
            ch = lambda k: res.get(k, {}).get("choices", [])  # noqa: E731
            rows.append({"annotator": title[6:], "crop_id": t["data"].get("item") or t["data"].get("crop_id"), "label": MAP.get((ch("label") or [None])[0]),
                         "reason": "|".join(ch("reason")), "obstacles": "|".join(ch("obstacles")),
                         "difficult": bool(ch("difficult")), "note": " ".join(res.get("note", {}).get("text", [])),
                         "seconds": a.get("lead_time"), "by": a.get("completed_by")})
lab = pd.DataFrame(rows)
if lab.empty:
    raise SystemExit("no annotations yet")
man = pd.read_csv(DATA / "manifest" / "pilot_v2.csv").rename(columns={"item": "crop_id"})
lab = lab.merge(man[["crop_id", "side", "street_id", "sampling_stratum"]], on="crop_id")
lab.to_csv(REP / f"pilot_labels_{stamp}.csv", index=False, encoding="utf-8-sig")

done = lab.groupby("annotator").crop_id.nunique()
print("done per annotator:", done.to_dict())
full = done[done >= MIN_DONE].index.tolist()
W = lab[lab.annotator.isin(full)].pivot_table(index="crop_id", columns="annotator", values="label", aggfunc="first").dropna()
out = [f"# Pilot report {stamp}", f"Annotators with >= {MIN_DONE} done: {full}; items labelled by all: {len(W)}", ""]
if len(full) >= 2 and len(W):
    out.append("| pair | κ 3-way (0/1/I) | raw agree | κ binary (both 0/1) | n binary |\n|---|---|---|---|---|")
    for a, b in itertools.combinations(full, 2):
        both = W[W[a].isin(["0", "1"]) & W[b].isin(["0", "1"])]
        out.append(f"| {a}–{b} | {cohen(W[a], W[b]):.2f} | {np.mean(W[a] == W[b]):.0%} | {cohen(both[a], both[b]):.2f} | {len(both)} |")
    tab = np.stack([(W == c).sum(1).values for c in ["0", "1", "I"]], 1)
    out.append(f"\nFleiss κ (3-way, {len(full)} annotators): **{fleiss(tab):.2f}**")
    maj = (tab.max(1) / len(full))
    W["majority_share"] = maj
    W["n0"], W["n1"], W["nI"] = tab[:, 0], tab[:, 1], tab[:, 2]
else:
    out.append("(need >= 2 finished annotators for agreement)")
L = lab[lab.annotator.isin(full) if full else slice(None)]
out += ["", "## Per annotator", L.groupby("annotator").agg(
    n=("crop_id", "size"), share0=("label", lambda x: (x == "0").mean()), share1=("label", lambda x: (x == "1").mean()),
    shareI=("label", lambda x: (x == "I").mean()), median_s=("seconds", "median"), difficult=("difficult", "mean")).round(2).to_markdown(),
        "", "## Labels by sampling stratum", pd.crosstab(L.sampling_stratum, L.label, normalize="index").round(2).to_markdown(),
        "", "## Insufficient reasons", L[L.label == "I"].reason.replace("", "(missing)").value_counts().to_markdown(),
        "", "## Labels by street", pd.crosstab(L.street_id, L.label, normalize="index").round(2).to_markdown()]
(REP / f"pilot_report_{stamp}.md").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))

if len(full) >= 2 and len(W):
    dis = W[W.majority_share < 0.8].sort_values("majority_share").head(40)
    dis.to_csv(REP / f"pilot_disagreements_{stamp}.csv", encoding="utf-8-sig")
    font, S_ = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 16), 300
    sheet = Image.new("RGB", (S_ * 5, S_ * int(np.ceil(len(dis) / 5)) or S_), "white")
    for k, (cid, r) in enumerate(dis.iterrows()):
        im = Image.open(DATA / "crops" / "pilot_v2" / f"{cid}.jpg").resize((S_, S_))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, S_, 22), fill=(0, 0, 0))
        d.text((4, 2), f"#{k} 0:{r.n0} 1:{r.n1} I:{r.nI}", fill=(255, 255, 0), font=font)
        sheet.paste(im, ((k % 5) * S_, (k // 5) * S_))
    sheet.save(REP / f"pilot_disagreements_{stamp}.jpg", quality=85)
    print("disagreement sheet:", len(dis), "items")
