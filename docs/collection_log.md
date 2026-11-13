# Collection log

## 2026-10-22 — Step 1: candidate streets

**Inputs**
- OSM via Overpass (snapshot 2026-10-22T02:26Z), bbox 10.745–10.815 N, 106.650–106.725 E: 7,283 named road ways, 6,715 POIs → `data/raw/osm/`.
- Mapillary metadata, 360° only (`is_pano=true`), 0.001° cells: 652,159 panos, 1,234 sequences; 2 tiny cells failed (near the bbox corner by the airport) → `data/raw/metadata/mapillary_pano_20261022.parquet`.
  - Sources: `bemaps3_sg` 407k (2016/2023/2024), `phoenix_mapping_front` 211k (2023), `phoenixmap_front` 22k (2023), others < 5k each.
  - The PoC under-counted panos because it queried without `is_pano`, so each cell was truncated at 2,000 images of all kinds.

**Matching** (`src/03_rank_streets.py`)
- A pano is assigned to a street when it is ≤ 20 m from the street and its travel bearing is ≤ 30° from the street axis. Result: 81.3% of panos matched.
- Alleys (Hẻm/Kiệt/Ngõ) are excluded.

**Finding: capture hours are unreliable** (`src/02b_check_capture_time.py`, 12 panos per creator×hour)
- Panos stamped 18–23 h and 0 h are daylight-bright (median brightness 150–190).
- Only panos stamped 1 h and 5 h are dark, about 11k of 650k.
- Decision: never filter by stamped hour. The night filter uses image brightness (upper half < 90).

**Preview** (`src/04_street_preview.py`): 56 streets, 20 positions each, 2,240 crops.
- Right-side crops (direction of traffic) usually show the near sidewalk. Left-side crops often show the roadway, the median or the far sidewalk. Expect a high "insufficient information" rate for left crops; check this in the pilot.
- The Mask2Former sidewalk fraction from this run is **invalid**: the current transformers version loads the checkpoint with missing Swin layernorm weights, and visible sidewalks score about 0. The metric was discarded. Mask2Former is not part of the official pipeline.
- `poc_blocked_share` = share of right-side daytime crops with PoC ConvNeXt P(không đi được) ≥ 0.5. It is a rough street-selection aid only: AI-made training labels, 20 crops per street, about ±20 percentage points.
- Outputs: `data/streets/street_candidates_v1.csv`, `street_preview_v1b.csv`, contact sheets `data/streets/preview/*.jpg`.

**Excluded on inspection**
- Võ Văn Kiệt, Trường Sa, Hoàng Sa, Tôn Đức Thắng, Nguyễn Hữu Cảnh: canal or riverside arterials with a sidewalk mostly on one side and few pedestrians. Võ Văn Kiệt and Tôn Đức Thắng also have 25–35% night crops.
- Cầu Thủ Thiêm (a bridge) and Mai Chí Thọ (tunnel approach road).

## 2026-10-22 — Pilot set (`src/05_make_pilot.py`)
- Streets: Pasteur, Lê Văn Sỹ, Phan Đăng Lưu (reserve streets; pilot labels go to train after adjudication).
- Positions sampled: 180; night panos dropped by brightness < 90: 2.
- Picked 75 panos -> 150 crops, stratified by PoC score terciles (sampling only, never shown).

## 2026-10-23 — Left vs right crops (`src/08_side_analysis.py`, exploratory)

Question raised while labelling: should only right-side crops be kept?

- **Data:** 1,166 daytime panos (street preview + pilot) → 2,332 crops.
- **Proxy:** "near sidewalk visible" from SegFormer-B5 Cityscapes on the bottom 45% of each crop. The proxy is strict: by eye it misses many usable right crops. Read it as a relative comparison only.
- **Proxy result:** near-sidewalk visible in **L 7% vs R 38%**.
  - Per pano: only R 36%, only L 5%, both 2%, neither 57%.
- **Eyeball check (Claude, 24 random pairs, not labels):** usable L about 3/24, R about 17/24. Left crops mostly show the roadway, a crosswalk, the median, the far side, or a passing vehicle.
- **Exceptions:** on a few one-way streets (Pasteur, Nguyễn Đình Chiểu, Trương Định) L ≥ R.
  - When the pano lies more than 4 m left of the OSM centreline: L 22% vs R 12%. This applies to only 7% of panos.
  - A "near-side by lateral offset" rule scores 34.8% vs 38.0% for R-only, because GPS and OSM noise misplaces the offset.
  - An oracle that picks the better side reaches 42.7%.
- **Coverage with R-only on the 12 draft streets:** the other sidewalk is covered by opposite-direction passes at 81–96% of positions on CMT8, Hai Bà Trưng, Nơ Trang Long and Lý Thường Kiệt. Coverage is low on one-way streets: Nguyễn Kiệm 0%, Hải Thượng Lãn Ông 21%, Nguyễn Đình Chiểu 22%, Trần Phú 23%.
  - Left crops do not fix this, because they rarely show that sidewalk either.
- **Proposed rule (to confirm with the pilot's human labels; the pilot keeps L+R as built):** main collection = **right-side crop only**.
- **Limitation to report:** left sidewalks of one-way streets are under-observed by vehicle imagery. Team-captured photos can target them.

## 2026-10-23 — Pilot v2 (`src/10_make_pilot_v2.py`)
- Replaces pilot v1 (L+R). 150 right-side crops, one per pano, yaw 60 deg from travel, pitch -4, FOV 90.
- Streets Pasteur, Lê Văn Sỹ, Phan Đăng Lưu: {'Lê Văn Sỹ': 50, 'Phan Đăng Lưu': 50, 'Pasteur': 50}; strata by PoC score terciles (sampling only).
- Opaque item codes shown to annotators; mapping to Mapillary ids in data/manifest/pilot_v2.csv.

## 2026-10-23 — Main collection v1 (`src/11_collect_main.py`, server)
- Streets/splits from configs/streets_v1.yaml; right crop yaw 60; <= 2 panos per 25 m position (distinct days); pilot positions skipped; cap 420 per street.
- Selected 3057 panos; status counts: {'ok': 2999, 'night': 58}.
- Crops kept: 2999 -> by split {'train': 1839, 'test': 674, 'val': 486}.

## 2026-10-29 — Pilot v2 results (`src/07_pilot_agreement.py`, report `data/labels/pilot_report/pilot_report_20261029_0903.md`)

**Data:** 5 annotators × 150 right crops, all complete.

**Agreement**
- Fleiss κ 3-way (0/1/I) = **0.57**, below the 0.6 gate.
- Eligibility (I vs 0/1): Fleiss κ = 0.65.
- 0 vs 1 on the 82 items all five called eligible: Fleiss κ = **0.49**. This is the weak point.
- Pairwise κ 3-way ranges 0.44–0.71. Binary κ is lowest for pairs with Loan (0.26–0.37).
- Share labelled blocked differs a lot by annotator: Loan 8%, Khai 12%, Hoc 15%, Phuc 16%, Minh 25%.

**Votes**
- 77 items unanimous, 38 at 4/5, 35 at ≤ 3/5.
- Majority label: 0 = 82, I = 44, 1 = 19, none = 5.
- Only 3 items are unanimous "blocked".

**Labelling behaviour**
- "Parked motorbike" was tagged 90× on items labelled 0 and 84× on items labelled 1. The 0/1 boundary for parked motorbikes is the main ambiguity.
- No notes were written. The difficult flag was used ≤ 1%.
- Median seconds per image: 4.7–12.6.
- Insufficient reasons: no near sidewalk 128, occluded 50, no sidewalk this side 33, blur 9.

**Usable share:** about 70% of crops (I ≈ 30%). Pasteur has 54% I.

**Disagreement themes**
- Which stretch counts (far obstacles).
- Thin or far sidewalk vs I.
- Intersections.
- Foreground occlusion.
- Width threshold for parked motorbikes.
- Fully covered sidewalk labelled I instead of 1.

**Response:** draft guide v1 (`guide/annotation_guide_v1_draft.md`, rules R1–R6) for the team meeting, then a 50-image check round before main labelling.

## 2026-11-01 — Repository scope

- The repository covers the stages up to and including labelling: collection, filtering, cropping, pilot and labelling.
- Removed from the earlier trial: everything after its labelling step (training, evaluation, demo app, trained model) and its documents. The trial's own collection scripts were dropped because `src/` replaces them.
- `src/collection/04_street_preview.py` and `src/labeling/10_make_pilot_v2.py` stay as the record of how streets and the pilot were chosen. Their scoring step needs the trial model, which is not in the repository, so they do not run as they stand. Results stay frozen in `configs/streets_v1.yaml`, `data/streets/` and `data/manifest/pilot_v2.csv`.
- Log entries above are unchanged. They record how the data were actually selected: the trial model's scores informed street choice and pilot stratification, and never produced labels.

## 2026-11-01 — Pilot review before the guide v1 meeting (`src/analysis/13_pilot_review.py`, `14_rule_check.py`, `15_theme_impact.py`)

The pilot numbers above are unchanged. This review reads them again; the team will meet to agree the rules.

- **Correction:** the entry of 2026-10-29 treated "parked motorbike tagged 90× on items labelled 0" as evidence of the 0/1 boundary. Tagging habits differ: Minh and Phuc tagged obstacles on 0% of their 0 labels, Hoc 21%, Khai 42%, Loan 54%. The figure mostly reflects that difference.
- **Direction of disagreement against the other four:** Loan said 0 on 14 of 21 items the others called blocked; Minh said 1 on 15 and I on 12 of the 84 items the others called 0. Hoc, Khai and Phuc sit between. This is relative to group consensus, not to a true label.
- **Eligibility rule, measured:** whether the sidewalk reaches below 60% of image height matches the group majority on 89% of items, 86% in 5-fold check; AUC 0.92. The best threshold ranged 0.60–0.75 in bootstrap.
- **Draft rule R2 rejected:** a sidewalk-width requirement lowered agreement to 81% or less.
- **Rules not validated:** a free strip measured from segmentation, in motorbike widths or as a ratio, did not predict votes (AUC 0.39–0.69, intervals include 0.5). Near versus middle zone showed no difference. R1 and R5 are conventions to be agreed, not measured results.
- **Obstacle quantity versus continuity:** parked-obstacle share predicts blocked votes (AUC 0.75). Visual review shows it is not the right criterion: items #21 and #26 have occupancy 0.53–0.60 and a clear path, while #13 has 0.09 and is blocked.
- **Theme impact (upper bound if settled):** far sidewalk 0.67, partial encroachment 0.67, foreground occlusion 0.63, intersections 0.63; the first two together 0.77.
- Theme assignment and suggested labels are Claude's visual review, for discussion only. They are not labels.

## 2026-11-01 — Insufficient-information reasons merged in the guide v1 draft

- Team feedback: the reasons "no near sidewalk seen" and "no sidewalk on this side" read alike, and the shorthand tags in the review sheets were hard to follow.
- Pilot evidence: 18 of the 19 images with a "no sidewalk on this side" vote also had a "not seen" vote; none was agreed on that reason alone. Merging raises reason agreement from 0.79 to 0.90 on the 54 images with at least 2 insufficient votes.
- Draft v1 uses one reason, "Không thấy vỉa hè", which also covers intersections and open forecourts; the separate intersection reason proposed earlier is dropped.
- Four reasons remain (keys F G H J), in `labeling/label_studio/ls_label_config_v1.xml`. Pilot labels stay as recorded. Label Studio projects are unchanged until the meeting closes the guide.

## 2026-11-04 — Train enrichment preview (`src/analysis/16_train_extra_preview.py`, `src/seg_measures.py`)

Question: the blocked class may be too small. Can more blocked crops be found for train without touching val/test? Summary for the team: `docs/data_enrichment.md`.

- **Estimate, not measured on the main set:** pilot 19/101 blocked (Wilson 95% 12–28%) × usable share 55–71% → train ~200–245 blocked (range ~125–360), test ~70–90 (~45–130).
- **Candidate pool tried:** panos ≤ 15 m from a train main_v1 pano, same travel direction (≤ 30°), on a capture day that position does not use, same creators and years as main_v1, not in main or the pilots. Metadata for the 662 cells around train positions: 109,403 panos. Pool: 1,850 (one per position and day), mostly Điện Biên Phủ#1 617, CMT8 468, Nguyễn Thị Minh Khai 350.
- **Preview, laptop CPU:** 155 sampled → 7 night, 148 crops; then 80 → 5 night, 75 crops. No near duplicates against the main crop of the same position (dHash ≤ 10 bits). One blue-cast crop passed the night filter. SegFormer-B5 on CPU about 6.7 s per crop.
- **Scorer:** `occ_v1` = `parked()` of `14_rule_check.py` (pilot AUC 0.75; top third with near_y ≥ 0.60 = 28% blocked vs 13% random). Its top ranks were foreground cars and vans and moving motorbikes. `occ_v2` drops blobs touching the bottom edge or > 15% of the image, blobs with more road than sidewalk under their lower third, and scores 0 when parked + sidewalk < 5% of the lower half. A person-near rule was tried and dropped (it removed a vendor cart). On 75 crops, by eye (not labels): about 6–7 of the v2 top 10 show parked rows or stalls vs 1–2 of 6 random. v2 still drops carts at the kerb; Cityscapes has no class for carts, goods or furniture.
- **Not validated:** `src/analysis/17_check_scorer_pilot.py` (paired bootstrap of AUC v2 − v1 on the pilot votes) is written but not run. The v2 rules were set after viewing the preview sheet.
- **Decision (team):** do not use this pool. Enrichment waits for the first labelling round and will come from new train streets (not other components of val/test streets), with a selector trained on first-round labels if it beats the occupancy scores on the pilot. Nothing was added to the manifests or Label Studio.
- `requirements.txt`: added scipy (already needed by `14_rule_check.py`).

## 2026-11-11 — Main labelling done (`src/labeling/19_main_agreement.py`, report `data/labels/main_report/main_report.md`)

**Data:** 5 annotators × 887 tasks = 4,435 annotations on 2,999 items, none missing. Three tasks were saved twice with the same label; the latest is kept. All MAIN projects ran the v1 interface, and no v0 reason is left.

**Agreement (Cohen κ, 3-way 0/1/I)**
- Test, Hoc–Loan, 674 items: **0.60**, raw 79%, binary κ 0.68 on 418 items.
- Val, Minh–Khai, 486 items: **0.64**, raw 80%, binary κ 0.55 on 211 items.
- Train cross-check, 276 items over 10 pairs: **0.61**, raw 78%. Pairs have 12–48 items, so per-pair values are noisy.
- Disagreements by type: 0/I 193, 0/1 59, 1/I 51. Most disagreement is about eligibility, not the 0/1 boundary.

**Provisional labels** (agreed or single; 303 open)
- 0 = 1,460, 1 = 145, I = 1,091, open = 303 (test 143, val 99, train 61).
- Blocked per split before adjudication: train 98 (at most 121 if every open item with a 1 vote went to 1), val 16 (≤ 54), test 31 (≤ 80).
- Blocked share among usable items is about 9%, half the pilot's 19%. The pilot was stratified by PoC score towards blocked-looking items; the main set is not.
- Insufficient share 36% overall. By street: Pasteur 81%, Hải Thượng Lãn Ông 57%, Điện Biên Phủ#1 54%, Trần Phú 53%, Lê Văn Sỹ 13%.

**Labelling behaviour**
- Median seconds per image: Hoc 2.1, Minh 2.3, Khai 3.4, Loan 5.9, Phuc 7.5. Labels under 2 s agree with the partner *more* often (test Hoc 82% vs 76%, val Minh 89% vs 73%), so fast labels mark easy images, not careless work.
- Blocked without an obstacle tag: Phuc 10/52, Loan 6/53, Khai 3/74, Hoc 0/88, Minh 0/45.
- Notes: 1. Difficult flag: Minh 12%, Phuc 4%, others 0%.

**Next:** adjudicate the 303 open items (Phuc), recount blocked per split, decide on the test streets if test has fewer than about 60 blocked items, then enrich train (`docs/data_enrichment.md`).

## 2026-11-11 — Adjudication proposal for the 303 disagreements (`data/labels/main_report/adjudication_proposal.csv`)

- Phuc confirmed guide v1 as written, including the "(chờ họp)" proposals: far obstacles count only up to about mid-image; no straight path means blocked; people do not count; cars are obstacles like any other.
- Claude looked at every item **blind** (only a number on the tile, no votes), 12 per sheet at 490 px with the 3/5 line drawn, and wrote a label and a reason. Then Claude compared the labels with the votes. On 21 items the label differed from both votes, so Claude looked again at 640 px with the votes shown, and changed 10 of them.
- Result: 0 = 96, 1 = 29, I = 178. 17 items are marked unsure; 11 differ from both votes. Agreement with each annotator's vote on these items: Loan 96/156, Minh 82/119, Phuc 26/43, Hoc 56/165, Khai 32/123. These are hard items by construction, so the rates do not rate the annotators.
- Most 0/I splits went to I (141 of 193): far sidewalk, intersections, alley mouths and riders next to the camera. When the curb did reach below the 3/5 line and the strip was clear, the item went to 0.
- These are **proposals, not final labels**. Phuc reviews `sheets/adjudication_proposal_*.jpg` and writes any override in the `phuc` column; `19_main_agreement.py` then uses `phuc` where given, else `proposed`.
- If every proposal is accepted: blocked train 102 / val 28 / test 44; usable (0/1) 1,042 / 235 / 453; blocked share about 10%. **Test is below the ~60 positives mark** set in `docs/data_enrichment.md`.
- Train enrichment is postponed (Phuc's decision).

## 2026-11-11 — Adjudication closed; final labels v1 (`data/labels/main_labels_v1.csv`)

- Phuc reviewed all 303 proposal tiles and overrode 28 (9.2%): I→0 12, 0→1 11, I→1 4, 1→0 1. Every override equals one of the two original votes. Phuc overrode 1 of the 17 items Claude marked unsure. (Tile 12, goods covering the sidewalk, was first set to 0 and then returned to the proposal, 1, under guide v1.)
- Final labels on the 303 items: 0 = 98, 1 = 43, I = 162.
- Final table, all 2,999 items: 0 = 1,558, 1 = 188, I = 1,253. Sources: agreed 1,133, single 1,563, adjudicated (proposal kept) 275, adjudicated (Phuc's label) 28.
- Usable (0/1) by split: train 1,045 (106 blocked, 10.1%), val 242 (35, 14.5%), test 459 (47, 10.2%).
- Phuc was one of the two annotators on 43 of the 303 items; the final label equals Phuc's vote on 27 of them (the blind proposal matched 26).
- Label Studio keeps each annotator's original votes; final labels live in the repo only. Summary for the report: `docs/labeling_phase1.md`.

## 2026-11-11 — Pilot items re-reviewed under guide v1 and added to train

- The 150 pilot items (train streets Pasteur, Lê Văn Sỹ, Phan Đăng Lưu; no position overlap with the main set) had 5 votes each under guide v0. All 150 were reviewed again under guide v1, not only the 35 items with ≤3/5 agreement, because v0 had no 3/5-line rule.
- Claude looked blind (shuffled order), then compared with the votes; 34 items had 0–1 votes for the proposal and were looked at again at 640 px with votes, and 20 were changed.
- Phuc reviewed the 5 sheets and changed 3: tile 6 (1→I: curb lies on the 3/5 line), tile 44 (0→1: motorbikes, tree and tables fill the width on the left), tile 123 (I→0).
- Final pilot labels: 0 = 73, 1 = 14, I = 63. 29 differ from the v0 majority, mostly far sidewalks, intersections and alley mouths that v1 sends to I.
- `data/labels/main_labels_v1.csv` now holds 3,149 items with columns `phase` (main/pilot) and `file`. Usable train 1,132 (120 blocked), val 242 (35), test 459 (47).
- Pilot items were sampled by PoC score strata, so their blocked share (16%) is not natural; EDA must split by `phase`.

## 2026-11-11 — Enrichment selector: benchmark written, not run (branch `enrichment-selector`)

Question: is there a better way to pick train crops for labelling than SegFormer occupancy (`occ_v2`)? Summary: `docs/data_enrichment.md` section 7.

- **New code:** `src/enrich.py` (pano fetch, crop rebuild from manifest yaw, frozen embeddings, logistic selector), `src/analysis/21_selector_benchmark.py` (leave-one-street-out comparison on train labels; val and test are not read), `src/analysis/22_enrichment_simulation.py` (does score-based picking help a downstream classifier). Scripts 21 and 22 are syntax-checked only. **No scorer results exist yet.**
- **Crops:** the laptop held 303 of 2,999 main crops. All 1,839 train crops were rebuilt from the panos and the manifest yaw; 5 checked against server crops differ by 1.35–1.5 grey levels on average (JPEG re-encoding).
- **Timing on the laptop CPU:** 1,518 panos in 890 s with 8 threads, Mapillary at times throttled to about 11 s per request. SegFormer-B5 about 11 s per crop (while downloads were running); CLIP ViT-B/16 0.19 s per crop (1,851 crops in 355 s).
- **Stopped** because of the missing GPU; the work continues on the PC. The area-wide metadata scan (script 02) was started and stopped without output.
- `requirements.txt`: added scikit-learn, sentencepiece, protobuf.
- Decision rule fixed before any result: replace the old selection only if the new scorer beats `occ_v2` on the hit rate in the top 20% (paired bootstrap 95% interval above 0) and is not worse on AP.

## 2026-11-11 — Enrichment selector: benchmark run, old selection replaced (branch `enrichment-selector`, PC with RTX 5060)

Summary and tables: `docs/data_enrichment.md` section 7.

- **Environment:** `.venv` with torch 2.11.0+cu128 (the Anaconda base has a CPU build). 1,778 missing train crops were rebuilt from the panos and the manifest yaw; all 1,989 train crops (1,839 main, 150 pilot) are present.
- **`21_selector_benchmark.py --seg-n -1`** ran without code errors. Added one column: per street, blocked crops in the scorer's top 20% against `occ_v2`. Measured on the 1,839 main-phase train crops (106 blocked, 5.8%), leave-one-street-out, val and test not read:
  - `occ_v2`: AP 0.138, hit rate in the top 20% 0.139. `occ_v1`: 0.136, 0.152. v1 − v2 on the top 20%: +0.014 [−0.014, +0.041].
  - `lr_dinov2_b14`: AP 0.398, AUC 0.877, top 10% 0.321, top 20% 0.220, top 33% 0.148. Against `occ_v2`: top 20% +0.082 [+0.043, +0.117], AP +0.259 [+0.161, +0.358] (paired bootstrap, 2,000 resamples within streets). Streets with more / equal / fewer blocked crops in the top 20% than `occ_v2`: 6 / 3 / 1.
  - The other logistic selectors (CLIP B/16, CLIP L/14, SigLIP B/16) also beat `occ_v2` with intervals above 0 (+0.059 to +0.063). No zero-shot scorer does.
  - Inner CV chose C = 0.001 (the lower edge of the grid) in nearly every fold. The grid was not changed after the run.
- **Decision (rule fixed before the run):** `lr_dinov2_b14` replaces `occ_v2`. DINOv2 was chosen among four encoders on the same data, so its own numbers are slightly optimistic.
- **`22_enrichment_simulation.py --enc dinov2_b14`**, 300 rounds, 20% of the pool labelled (112 crops on average): blocked crops picked: random 6.4, 70/30 rule 19.7, top 22.3. AP of a linear probe on held-out train streets against random: 70/30 +0.014 ± 0.005, top +0.019 ± 0.005, whole pool +0.030 ± 0.005. Rounds reuse the same 10 streets, so the intervals are too narrow. Fixed two pandas-to-numpy masks before the run.
- **Pool size:** hit rate of the 70/30 rule at 10% / 20% / 36% of the pool: 0.282 / 0.202 / 0.132.
- **New: `src/collection/23_collect_train_extra.py`, `configs/streets_train_extra.yaml`** (10 candidate streets, `status: proposed`; `streets_v1.yaml` unchanged). Guard tested: `Nguyễn Đình Chiểu#1` is refused.
  - `--all`: 1,127 panos on 611 positions (15 positions within 40 m of a val/test pano and 3 already used were dropped); 1 night pano, no duplicates; 1,126 crops scored by `lr_dinov2_b14_C0.001` fitted on 1,989 train crops (120 blocked).
  - Selection: 400 crops = 280 by score (at most 70 per street; largest share 42) + 120 random. Written to `data/manifest/train_extra_v1.csv` (`phase=train_extra`, `stratum`, `score`, `selector`, `streets_status=proposed`). Sheet: `docs/figures/train_extra_v1_sheet.jpg`.
  - Timing: 1,127 panos in 246 s; DINOv2 on 1,066 crops about 16 s with model load; SegFormer-B5 on 1,839 crops 167 s.
- **Old pipeline:** the `--all` selection of `16_train_extra_preview.py` was removed (preview kept); `17_check_scorer_pilot.py` is marked superseded and was never run.
- **Not done / not verified:** nothing was uploaded to Label Studio; no human label exists on the new streets, so the hit rate there is unknown; the street list and the 400 crops are proposals for the team.

## 2026-11-11 — Street scan with the selector (`src/analysis/24_street_scan.py`)

Question: which streets should train enrichment draw from? Summary and table: `docs/data_enrichment.md` section 8.

- **Check on train first:** over the 10 train streets, the mean leave-one-street-out selector score of a street against its labelled blocked share: Spearman 0.96. The old preview score (`street_preview_v1b.csv`) reaches 0.40 on the same streets.
- **Scan:** 150 streets with >= 30 positions, not in `streets_v1.yaml`, no val/test street name; 30 random 25 m cells per street, one pano each. 4,500 panos in 871 s, 100 night, 4,400 crops scored by `lr_dinov2_b14_C0.001`.
- **Result:** street mean scores from 0.02 to 0.67 (median 0.28). The top 20 are mostly small streets near markets (Phạm Hữu Chí#0, Nhật Tảo, Tôn Đản, Thích Quảng Đức, Hoàng Hoa Thám, ...), mean about 0.58. The 10 streets proposed on 2026-11-04 rank 34 to 103, mean 0.32.
- **Limits:** train, val and test streets are all large roads, so the selector is unverified on small streets; ranking 150 streets on 30 crops each makes the top optimistic; the mapping from score to blocked share is a line through 10 points and an extrapolation above 0.43; no human label exists on any scanned street.

## 2026-11-11 — Train enrichment list: 2,000 crops from 75 streets (`src/collection/23_collect_train_extra.py --all --n 2000`)

Summary: `docs/data_enrichment.md` section 9.

- **Decision (Phuc):** one labelling round only, 2,000 crops, 400 per annotator, one annotator per crop.
- **Streets:** `configs/streets_train_extra.yaml` now holds the 75 streets with the highest scan score (>= 0.275): 10 primary, 13 secondary, 44 tertiary, 8 residential; `status: approved` (Phuc). Pool by `--dry`: 50 streets 3,137 panos, 75 streets 5,074, 100 streets 7,511.
- **Script 23:** `--n` (default 2,000) replaces the fixed 400; it also writes `data/manifest/train_extra_v1_assignment.csv`.
- **Run:** 5,074 panos on 3,077 positions (57 positions within 40 m of a val/test pano and 37 already used were dropped) in 911 s; 38 night, 1 near duplicate, 5,035 crops scored by `lr_dinov2_b14_C0.001` in 54 s.
- **Selection:** 2,000 crops = 1,400 by score (score >= 0.61; at most 350 per street, largest 101) + 600 random. By road type: tertiary 1,230, secondary 374, primary 207, residential 189. Largest streets: Hoàng Sa 157, Trường Sa#0 117.
- **Assignment:** Hoc, Khai, Loan, Minh, Phuc, 400 crops each, at random.
- An earlier run of the same day (10 old candidate streets, 400 crops, PR #3) is replaced by this one.
- **Not verified:** no human label on any new street; 71% of the crops come from small streets while train, val and test are large roads; no double labelling, so no agreement figure for these crops.

## 2026-11-11 — Train enrichment crops on Label Studio (`src/labeling/25_ls_create_train_extra.py --apply`)

- **Decision (Phuc):** upload now, without the sample-sheet meeting planned in `docs/data_enrichment.md` section 5.
- The 2,000 selected crops were copied to the server (`/srv/sidewalk/data/crops/train_extra_v1`, 201 MB; md5 of 3 files equal to the PC copies).
- Five new projects `MAIN2_<name>` (ids 13 to 17), 400 tasks each from `train_extra_v1_assignment.csv`, private random order, v1 interface and guide v1. A task holds the image and the item code only.
- Separate projects, not mixed into `MAIN_*` as first planned: the `MAIN_*` projects are the closed record of round 1 and `19_main_agreement.py` reads every `MAIN_*` project.
- Checked after the import: 400 tasks and no annotation in each project; 60 random images are served; the task list of `MAIN2_Phuc` equals the assignment; the five `MAIN_*` projects still show 887 of 887.

## 2026-11-12 — Train enrichment labels done (`src/labeling/26_train_extra_report.py --fresh`, report `data/labels/train_extra_report/report.md`)

- 2,000/2,000 crops labelled, none missing, no task saved twice. 0 = 810, 1 = 588, I = 602. Labels: `data/labels/train_extra_labels_v1.csv` (kept separate from `main_labels_v1.csv`).
- Train after enrichment: 708 blocked of 2,530 usable (before: 120 of 1,132).
- **Selector on the new streets:** top_score stratum (all 1,400 pool crops with score >= 0.61) 541 blocked = 0.386 [0.361, 0.412]; random stratum (600 of the other 3,635) 47 = 0.078 [0.059, 0.103]. Estimated blocked share of the whole pool 0.164 [0.148, 0.182], so the 2,000 picked crops hold 1.8x what random labelling of the pool would give (588 vs about 328). The top stratum (28% of the pool) holds about 66% [60%, 72%] of the pool's blocked crops. Blocked share rises with the score: 0.02 below 0.2 up to 0.54 above 0.9.
- **Street choice:** pool base rate 0.164 against 0.058 on the 10 old train streets. Street scan score against the pool-weighted blocked share of 62 streets with >= 3 random crops: Spearman 0.55.
- **Annotators differ beyond chance** on randomly assigned crops (chi-square p = 4e-15 on all 2,000; p = 0.001 on the random stratum): blocked per crop Hoc 0.43, Khai 0.31, Phuc 0.28, Minh 0.25, Loan 0.19; random stratum Hoc 16/108, Loan 1/120. One annotator per crop, so it is not known who is right.
- Obstacles on blocked crops: parked motorbikes 351, goods / stalls 221, other 66, tables and chairs 49, barriers / works 38, parked cars 11. Reasons for I: no sidewalk seen 463, covered 106, blurred / dark / overexposed 21, other 9.

## 2026-11-13 — Eye review of the train-extra labels tried and dropped

- Claude re-read 788 crops (all 588 labelled 1 + 200 random of the 0/I crops): blind pass, then a second look at the 288 crops where the blind proposal differed from the annotator's label (13 sheets by Claude, 19 by a Sonnet subagent). 264 proposals still differed from the original labels; Claude proposed changing 212 of the 588 blocked labels (Hoc 47%, Khai 38%, Phuc 35%, Minh 26%, Loan 24%).
- **Decision (Phuc):** most of Claude's changes looked wrong on the sheets, so the review is dropped and the team's labels stay as they are. `data/labels/train_extra_labels_v1.csv` is the final table; no v2 was written. The review script and its output (never committed) were deleted.
- Not measured: how many of Claude's proposals were right; nobody checked the crops one by one.
- Still true: annotators differ beyond chance on randomly assigned crops (section above), one annotator per crop, no second check.

## 2026-11-14 — Cross-check of the train-extra labels by a team member

- A team member cross-checked the list of 264 crops that Claude had doubted on 2026-11-13 (numbered as the sheets of that review). The review folder had been deleted, so the sheet-tile to item map was rebuilt: the blind sample from the same seeded code, the blind proposals recovered from the tool calls in the session transcript (788 of 788 tiles, no conflicts), and the 35 second-look changes. Every number printed during the review is reproduced (sample 126 zeros + 74 I, crops per annotator 203/175/116/152/142, blind agreement 0.635, 264 tiles, 12/12, 140/72, 10/18).
- The cross-check has labels for 203 tiles. It equals the original label on 186 (92%) and Claude's proposal on 1. 61 tiles have no label (original kept). Tile 264 appears twice (0 and I) and tile 263 is missing: both kept as originally labelled (I) until the checker confirms.
- **17 labels change:** 1 to 0: 10; 1 to I: 4; I to 1: 2; 0 to 1: 1 (original annotator Hoc 10, Minh 4, Phuc 3; 14 in the top_score stratum, 3 in random). `data/labels/train_extra_labels_v2.csv` (columns `label_v1`, `source` = single / cross_check) is the new table, `data/labels/train_extra_cross_check.csv` the 203-row record. v1 is kept.
- After the cross-check: 0 = 819, 1 = 577, I = 604; top_score 531/1,400 = 0.379, random 46/600 = 0.077. Train: 697 blocked of 2,528 usable (before: 120 of 1,132). The report of 2026-11-12 and `report.md` are computed on v1.
- Only 203 of 2,000 crops have a second opinion, and they were picked because Claude doubted them.

