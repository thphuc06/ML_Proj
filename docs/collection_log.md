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
