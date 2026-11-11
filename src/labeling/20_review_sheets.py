"""Step 3d (adjudication): contact sheets for eye review of main items.
Each tile = one crop with its number, item id and a caption; the blue line marks 3/5 of the height (guide v1, Câu 2).
- default: the open disagreements (main_adjudicate.csv), caption = both votes, e.g. "Hoc 0 | Loan I"
- --proposal FILE: a CSV with columns item, proposed (0/1/I) [, split, unsure, why]; caption = the proposed label,
  large, so a reviewer can zoom and check by eye ("?" = the proposer was unsure). Tiles are grouped by label.
Crops come from data/crops/main/ (download them first with --fetch, read-only from Label Studio).
Output: data/labels/main_report/sheets/<name>_NN.jpg (gitignored)
Pilot items: --crops pilot_v2 --proposal data/labels/pilot_report/pilot_adjudication_proposal.csv
Usage: python src/labeling/20_review_sheets.py [--fetch] [--proposal path.csv] [--crops main|pilot_v2] [--cols 6 --rows 5]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ holds common.py, ls_client.py

import argparse

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from common import DATA

ap = argparse.ArgumentParser()
ap.add_argument("--proposal")
ap.add_argument("--fetch", action="store_true")
ap.add_argument("--crops", default="main")
ap.add_argument("--cols", type=int, default=6)
ap.add_argument("--rows", type=int, default=5)
args = ap.parse_args()

REP, CROPS = DATA / "labels" / "main_report", DATA / "crops" / args.crops
OUT = REP / "sheets"
OUT.mkdir(parents=True, exist_ok=True)
NAME = {"0": "0 Còn lối", "1": "1 Bị chặn", "I": "I Không đủ"}
COLOR = {"0": (40, 160, 70), "1": (215, 40, 40), "I": (110, 110, 110)}
T, BAR = 340, 30
f_small = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 17)
f_big = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 30)

adj = pd.read_csv(REP / "main_adjudicate.csv", dtype=str)
if args.proposal:
    df = pd.read_csv(args.proposal, dtype=str)
    if "split" not in df:
        df = df.merge(adj[["item", "split"]], on="item", how="left")
    df["order"] = df.proposed.map({"1": 0, "0": 1, "I": 2})
    df = df.sort_values(["order", "split", "item"]).reset_index(drop=True)
    name = Path(args.proposal).stem
else:
    df = adj.sort_values(["split", "pair", "street_id"]).reset_index(drop=True)
    name = "disagree"

if args.fetch:
    from ls_client import BASE, session
    s = session()
    CROPS.mkdir(parents=True, exist_ok=True)
    for i in df.item:
        p = CROPS / f"{i}.jpg"
        if not p.exists():
            r = s.get(BASE + f"/data/local-files/?d=crops/{args.crops}/{i}.jpg", timeout=60)
            r.raise_for_status()
            p.write_bytes(r.content)


def tile(k, r):
    im = Image.open(CROPS / f"{r['item']}.jpg").convert("RGB").resize((T, T))
    d = ImageDraw.Draw(im)
    y = int(T * 0.6)
    d.line((0, y, T, y), fill=(40, 140, 255), width=2)
    d.rectangle((0, 0, T, BAR), fill=(0, 0, 0))
    if args.proposal:  # label in a coloured top bar, so the near sidewalk (bottom of the crop) stays visible
        lab = NAME[r.proposed] + (" ?" if str(r.get("unsure")) == "True" else "")
        d.rectangle((0, 0, T, 42), fill=COLOR[r.proposed])
        d.text((6, 4), lab, fill=(255, 255, 255), font=f_big)
        d.text((T - d.textlength(f"#{k}", font=f_small) - 6, 11), f"#{k}", fill=(255, 255, 255), font=f_small)
    else:
        d.text((6, 3), f"#{k} {r.split[:2]} {r.annotator1} {r.label1} | {r.annotator2} {r.label2}", fill=(255, 230, 0), font=f_small)
    return im


per = args.cols * args.rows
for s0 in range(0, len(df), per):
    chunk = df.iloc[s0:s0 + per]
    sheet = Image.new("RGB", (args.cols * (T + 4), ((len(chunk) - 1) // args.cols + 1) * (T + 4)), "white")
    for j, (k, r) in enumerate(chunk.iterrows()):
        sheet.paste(tile(k, r), ((j % args.cols) * (T + 4), (j // args.cols) * (T + 4)))
    sheet.save(OUT / f"{name}_{s0 // per + 1:02d}.jpg", quality=88)
df.drop(columns=["order"], errors="ignore").to_csv(OUT / f"{name}_index.csv", encoding="utf-8-sig")
print(len(df), "tiles ->", OUT, f"({(len(df) - 1) // per + 1} sheets)")
