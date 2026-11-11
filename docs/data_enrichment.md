# Bơm thêm ảnh "Bị chặn" cho tập train

Ghi chép ngày 04/11/2026, cập nhật 11/11/2026. **Trạng thái: chưa bơm ảnh nào. Bộ chọn ảnh mới (embedding DINOv2 + logistic) đã đo xong và thay bộ chấm `occ_v2` (mục 7). Đã có danh sách 400 ảnh đề xuất từ 10 đường đề xuất, chờ nhóm chốt đường và duyệt tấm ảnh mẫu.** Đã gán xong bộ chính, số ảnh "Bị chặn" thật thấp hơn ước tính (xem mục 1). Nhóm quyết định chờ gán xong đợt đầu rồi mới xem xét bơm thêm, và lấy ảnh từ **đường train mới**. Nhật ký kỹ thuật ở [collection_log.md](collection_log.md).

## Bàn giao (11/11/2026)

Đợt gán nhãn 1 đã xong, đây là đầu vào cho việc bơm ảnh:

- **Nhãn chính thức:** [data/labels/main_labels_v1.csv](../data/labels/main_labels_v1.csv), mỗi ảnh một dòng, gồm các cột `item`, `split`, `street_id`, `label` (0/1/I) và `source`. Ghép với [main_v1.csv](../data/manifest/main_v1.csv) (dòng `phase=main`) hoặc [pilot_v2.csv](../data/manifest/pilot_v2.csv) (dòng `phase=pilot`) theo `item` để lấy metadata Mapillary. Quy trình gán và phân xử: [labeling_phase1.md](labeling_phase1.md).
- **Bước 1 của mục 5 đã xong.** Số ảnh "Bị chặn" / số ảnh dùng được: train 120/1.132 (gồm 150 ảnh pilot, trong đó 14 ảnh Bị chặn), val 35/242, test 47/459.
- **Bước 2–4 của mục 5 đã có bản đề xuất** (mục 7): 10 đường đề xuất và 400 ảnh đề xuất, chờ nhóm chốt. Bộ chọn ảnh train trên mọi nhãn train của file trên (`split == "train"`), với mục tiêu "Bị chặn" so với phần còn lại, gồm cả "Không đủ thông tin".
- **Test có 47 ảnh dương**, dưới mốc khoảng 60 ảnh. Nhóm chưa quyết định có đổi hay thêm đường test. Bơm ảnh chỉ vào train nên không phụ thuộc vào quyết định này. Nhưng **không được lấy đường mới từ danh sách đường val hoặc test**.
- Ảnh bơm thêm cần gán theo [guide v1](../labeling/guide/annotation_guide_v1_draft.md), bản đã chốt nguyên văn.

## 1. Vấn đề

Lớp "Bị chặn" hiếm, nên có thể không đủ ảnh để train và đánh giá.

**Nhãn cuối của bộ chính (11/11, sau phân xử):** train 106/1.045 ảnh dùng được (cộng 150 ảnh pilot thì 120/1.132), val 35/242, test 47/459 ([tổng kết](labeling_phase1.md)). Số trước phân xử:

| Tập | Số ảnh | Bị chặn: đồng thuận hoặc một người gán | Thêm nếu mọi ca bất đồng có phiếu 1 đều thành 1 | Ước lượng cũ |
|---|---|---|---|---|
| Train | 1.839 | 98 | +23 → tối đa 121 | ~200–245 |
| Val | 486 | 16 | +38 → tối đa 54 | ~50–65 |
| Test | 674 | 31 | +49 → tối đa 80 | ~70–90 |

Tỉ lệ "Bị chặn" trên các ảnh dùng được là khoảng **9%**, bằng một nửa con số 19% của pilot. Pilot được lấy mẫu nghiêng về phía ảnh trông như bị chặn, còn bộ chính thì không. Hệ quả:
- Train cần bơm, và bơm khoảng 400 ảnh có thể chưa đủ. Nếu bộ chọn ảnh đạt tỉ lệ trúng khoảng 28% như trên pilot, 400 ảnh cho thêm khoảng 110 ảnh dương.
- Test có thể dưới mức khoảng 60 ảnh dương. Cần quyết định về đường test **trước khi** bơm.

Ước lượng cũ (04/11), nhân từ ba nguồn:

- tỉ lệ "Bị chặn" trong pilot: 19/101 ảnh đa số chọn 0 hoặc 1, khoảng tin cậy 95% (Wilson) là 12–28%;
- tỉ lệ ảnh dùng được: 55% (40 ảnh xem bằng mắt, [feasibility_log.md](feasibility_log.md)) hoặc 71% (pilot);
- số ảnh của từng tập.

| Tập | Số ảnh | Bị chặn: thấp | Ước lượng | Cao |
|---|---|---|---|---|
| Train | 1.839 | ~125 | ~200–245 | ~360 |
| Val | 486 | ~35 | ~50–65 | ~95 |
| Test | 674 | ~45 | ~70–90 | ~130 |

- Train khoảng 200 ảnh dương là **đủ** để fine-tune hoặc linear-probe một backbone pretrained, nếu dùng class weight hoặc sampler cân bằng.
- **Tập test là chỗ đáng lo hơn.** Với khoảng 70–90 ảnh dương, khoảng tin cậy của F1 rộng khoảng ±0,1. Lý Thường Kiệt chiếm 285/674 ảnh test và có điểm preview thấp.
- Pilot chỉ lấy từ 3 đường train, Pasteur có 54% ảnh "Không đủ thông tin", nên tỉ lệ trên bộ chính có thể khác.

## 2. Nguyên tắc

1. **Chỉ bơm vào train.** Val và test giữ phân phối tự nhiên để kết quả đánh giá trung thực.
2. **Điểm của model chỉ dùng để chọn ảnh, không bao giờ là nhãn.** Ghi tầng và điểm của từng ảnh vào manifest. Giữ khoảng 30% ảnh bốc ngẫu nhiên, để không chỉ bơm loại "chặn vì xe".
3. **Không dùng YOLO hay model nào để gán nhãn thay người.** Lý do: model không thấy được sự liên tục của lối đi, nhãn sẽ bị vòng lặp (model học lại chính quy tắc của YOLO), và đề cương quy định nhãn do người gán. YOLO dùng được để chọn ảnh, làm baseline cho báo cáo, và phân tích lỗi. **Không hiện gợi ý của model trên Label Studio**, vì người gán sẽ bị neo theo gợi ý.
4. **Không nới định nghĩa "Bị chặn" chỉ để có thêm ảnh dương.** Định nghĩa chốt trong buổi họp, dựa trên câu hỏi gốc "có phải bước xuống lòng đường không". Có một gợi ý cho buổi họp: thêm ô phụ **"Lối hẹp, chỉ đủ 1 người"** khi chọn "Còn lối đi". Nhãn chính vẫn giữ định nghĩa chặt, nhưng sau này có thể làm thêm thí nghiệm với định nghĩa rộng.

## 3. Thử nghiệm ngày 04/11

Script: [16_train_extra_preview.py](../src/analysis/16_train_extra_preview.py), [seg_measures.py](../src/seg_measures.py), [17_check_scorer_pilot.py](../src/analysis/17_check_scorer_pilot.py). Chạy trên laptop, không đưa ảnh nào lên server.

### Kho ảnh thử: ngày chụp khác, cùng vị trí của bộ chính

Ứng viên là các pano cách ảnh main ≤15 m, đi cùng chiều (lệch ≤30°), chụp vào ngày vị trí đó chưa dùng, cùng nhóm người chụp và năm chụp với bộ chính. Tổng cộng **1.850 ảnh**, dồn chủ yếu vào 3 đường:

| Đường | Ảnh thêm | Đường | Ảnh thêm |
|---|---|---|---|
| Điện Biên Phủ#1 | 617 | Nguyễn Kiệm#0 | 86 |
| Cách Mạng Tháng Tám#0 | 468 | Trần Hưng Đạo | 70 |
| Nguyễn Thị Minh Khai | 350 | Nguyễn Trãi | 67 |
| Hải Thượng Lãn Ông | 107 | Phan Đăng Lưu | 49 |
| Lê Văn Sỹ | 25 | Pasteur | 11 |

### Bộ chấm điểm (SegFormer-B5 Cityscapes)

- `occ_v1`: tỉ lệ vỉa hè ở nửa dưới ảnh bị xe đậu chiếm, giống hệt `14_rule_check.py`. Trên pilot, chỉ số này có AUC 0,75 khi dự đoán ảnh bị chặn.
- `occ_v2`: như v1, nhưng bỏ xe sát camera (chạm mép dưới ảnh hoặc chiếm >15% ảnh), bỏ xe đứng trên lòng đường, và cho điểm 0 khi phần vỉa hè thấy được quá ít.

Tỉ lệ ảnh bị chặn trên pilot theo cách chọn:

| Cách chọn | Bị chặn / ảnh |
|---|---|
| Bốc ngẫu nhiên | 13% |
| Chỉ giữ ảnh thấy vỉa hè gần (`near_y ≥ 0,6`) | 17%, vẫn giữ 19/20 ảnh bị chặn |
| Thấy vỉa hè và nằm trong 1/3 điểm `occ_v1` cao nhất | **28%** |
| 1/3 điểm model PoC cao nhất (lúc lấy mẫu pilot) | 25% |

### Quan sát, do Claude xem ảnh, không phải nhãn

Ảnh: [figures/train_extra_preview_sheet.jpg](figures/train_extra_preview_sheet.jpg). Mỗi cặp gồm ảnh mới (trái) và ảnh main cùng vị trí, khác ngày (phải).

- **Pipeline chạy được.** Ảnh mới khớp vị trí và góc nhìn với ảnh main, khác ngày thì vật cản cũng khác, không có ảnh gần trùng (dHash). Bộ lọc đêm loại 7/155 và 5/80 ảnh. Có một ảnh bị ám xanh vẫn lọt bộ lọc.
- **`occ_v1` xếp sai ở phần đầu danh sách:** ô tô hoặc xe van sát camera, và xe máy đang chạy có người lái, được chấm cao nhất.
- **`occ_v2` loại được các ảnh sai đó.** Trên 75 ảnh, khoảng 6–7/10 ảnh top là đúng loại cần tìm (dãy xe đậu, sạp hàng, hàng rong), trong khi ảnh ngẫu nhiên chỉ khoảng 1–2/6. Nhưng v2 vẫn loại nhầm xe đẩy hàng nằm sát mép đường.
- **Giới hạn từ gốc của cách này:** Cityscapes không có lớp xe đẩy, hàng hóa, bàn ghế, và occupancy đo lượng xe chứ không đo lối đi có liên tục hay không. Các quy tắc của v2 được đặt ra sau khi nhìn ảnh, nên **chưa được kiểm chứng**. Script 17 (so v1 và v2 trên phiếu pilot, bootstrap theo cặp) đã viết nhưng **chưa chạy**; phép kiểm chứng đã được làm bằng script 21 trên nhãn train (mục 7).
- SegFormer-B5 trên CPU laptop mất khoảng 6,7 giây mỗi ảnh. Toàn bộ 1.850 ảnh cần PC có GPU.

## 4. Quyết định

1. **Lấy ảnh từ đường train mới, không lấy thêm ngày khác ở đường cũ.** Ảnh cùng chỗ ít đa dạng (cùng mặt tiền, model dễ học thuộc nơi chốn), và các đường train cũ có thể ít bị lấn chiếm.
2. **Bơm sau đợt gán đầu.** Lúc đó biết chắc train và test thiếu ảnh dương tới đâu, và có nhãn người để xây bộ chọn ảnh tốt hơn.
3. **Bộ chọn ảnh ưu tiên:** đặc trưng CLIP hoặc DINOv2 cộng logistic regression, train trên nhãn train của đợt đầu (active learning). Trước khi dùng, so trên pilot với `occ_v1`, `occ_v2` và CLIP zero-shot, theo AUC và tỉ lệ trúng ở top 1/3, rồi chọn bộ tốt nhất.

## 5. Khi tiến hành

1. Đếm số ảnh "Bị chặn" thực tế của từng tập sau đợt gán đầu.
2. Chọn đường train mới. Ứng viên có điểm preview cao, chưa dùng ở đâu ([street_preview_v1b.csv](../data/streets/street_preview_v1b.csv); điểm theo đường chỉ là gợi ý, sai số khoảng ±20 điểm %): Cao Thắng 0,53 · Hưng Phú 0,45 · Lê Quang Định#0 0,45 (Chợ Bà Chiểu) · Trần Xuân Soạn 0,40 · Đinh Bộ Lĩnh 0,35 · Nguyễn Chí Thanh#0 0,35 · Ngô Quyền 0,30 (Chợ Nhật Tảo) · Sư Vạn Hạnh 0,30 · Bình Đông 0,30 · Lê Đại Hành 0,30.
   - **Không dùng đoạn khác của đường val hoặc test**, ví dụ Nguyễn Đình Chiểu#1, để giữ đúng câu hỏi "đường chưa thấy".
   - Danh sách đề xuất nằm ở [configs/streets_train_extra.yaml](../configs/streets_train_extra.yaml) (`status: proposed`). Khi nhóm chốt thì đổi thành `approved` và ghi đường vào `configs/streets_v1.yaml` với `split: train`.
3. Chạy [23_collect_train_extra.py](../src/collection/23_collect_train_extra.py) (đã viết và chạy 11/11, xem mục 7). Script dùng `data/streets/pano_street_match_v1.parquet`; chỉ cần chạy lại 01–03 khi máy chưa có file này.
4. Chọn khoảng 400 ảnh: khoảng 70% theo điểm, mỗi đường tối đa 25% phần này, cộng khoảng 30% ngẫu nhiên. Ghi `phase=train_extra` và `stratum` vào manifest.
5. Cho cả nhóm xem trước một tấm ảnh mẫu, rồi mới trộn ảnh vào các project `MAIN_*`. Người gán không biết ảnh nào là ảnh bơm.
6. Trong EDA và báo cáo, tách số liệu "main tự nhiên" và "train_extra" riêng.

## 6. Chạy lại thử nghiệm

```bash
python src/analysis/16_train_extra_preview.py --dry          # đếm kho ứng viên, cần MAPILLARY_TOKEN
python src/analysis/16_train_extra_preview.py --sample 80    # tập nhỏ, tấm ảnh ở data/crops/train_extra_sheet.jpg
```

Script 16 không còn chế độ chọn ảnh `--all` (bỏ ngày 11/11, xem mục 7). Script 17 chưa từng chạy và đã được script 21 thay thế; giữ lại làm bản ghi.

Ảnh, mask và metadata được lưu trong `data/raw/` và `data/crops/`, không đưa lên git. Bảng điểm của tập nhỏ: [train_extra_preview_scores.csv](../data/streets/train_extra_preview_scores.csv).

## 7. Bộ chọn ảnh mới: kết quả và quyết định (11/11/2026)

**Kết luận: logistic regression trên embedding DINOv2 ViT-B/14 (`lr_dinov2_b14`) thay bộ chấm `occ_v2`.** Đo trên 1.839 ảnh main của train (106 ảnh "Bị chặn"), kiểu giữ nguyên một đường ra ngoài. Chưa ảnh nào được đưa lên Label Studio.

### Cách đo

- **Chỉ dùng nhãn train.** Không đọc nhãn val và test, kể cả để chọn encoder.
- **Giữ nguyên một đường ra ngoài:** ảnh của mỗi đường được chấm bởi model chỉ thấy 9 đường train còn lại, giống tình huống thật là chấm ảnh của đường mới.
- **Mục tiêu:** 1 nếu "Bị chặn", 0 cho cả "Còn lối đi" lẫn "Không đủ thông tin". Tỉ lệ trúng khi đó là số ảnh "Bị chặn" trên mỗi ảnh người phải gán.
- **Đo trên 1.839 ảnh main của train** (phân phối tự nhiên, 106 ảnh dương, tức 5,8%). 150 ảnh pilot chỉ dùng để fit, vì được lấy mẫu lệch.
- **Chỉ số:** AP, AUC, tỉ lệ trúng ở top 10% / 20% / 33%, và mô phỏng quy tắc của mục 5 (70% theo điểm, trần 25% mỗi đường, 30% ngẫu nhiên). Khoảng tin cậy 95% bằng bootstrap theo cặp so với `occ_v2` (2.000 lần, lấy lại mẫu trong từng đường).
- **Quy tắc quyết định, đặt trước khi xem số:** thay pipeline cũ chỉ khi bộ mới hơn `occ_v2` về tỉ lệ trúng ở top 20% (khoảng tin cậy 95% của hiệu nằm trên 0) và không kém về AP.

### Kết quả so bộ chấm ([21_selector_benchmark.py](../src/analysis/21_selector_benchmark.py))

SegFormer chạy trên toàn bộ 1.839 ảnh, nên mọi bộ chấm được so trên cùng một tập. Bảng đầy đủ: [selector_benchmark.csv](../data/streets/selector_benchmark.csv); điểm từng ảnh: [selector_benchmark_scores.csv](../data/streets/selector_benchmark_scores.csv).

| Bộ chấm | AP | AUC | Trúng top 10% | Trúng top 20% | Trúng top 33% | Quy tắc 70/30 ở 20% | Hiệu top 20% so với `occ_v2` [95%] | Số đường hơn / bằng / kém `occ_v2` |
|---|---|---|---|---|---|---|---|---|
| Bốc ngẫu nhiên | 0,058 | 0,50 | 0,058 | 0,058 | 0,058 | 0,058 | | |
| `occ_v1` (cũ) | 0,136 | 0,715 | 0,174 | 0,152 | 0,116 | 0,119 | +0,014 [−0,014; +0,041] | 3 / 5 / 2 |
| `occ_v2` (cũ, đang dùng) | 0,138 | 0,684 | 0,185 | 0,139 | 0,106 | 0,121 | | |
| CLIP B/16 zero-shot | 0,231 | 0,788 | 0,239 | 0,160 | 0,124 | 0,149 | +0,021 [−0,014; +0,057] | 5 / 1 / 4 |
| CLIP L/14 zero-shot | 0,134 | 0,687 | 0,147 | 0,122 | 0,100 | 0,109 | −0,017 [−0,052; +0,019] | 4 / 0 / 6 |
| SigLIP B/16 zero-shot | 0,215 | 0,767 | 0,239 | 0,152 | 0,113 | 0,144 | +0,015 [−0,024; +0,054] | 4 / 0 / 6 |
| Logistic trên CLIP B/16 | 0,323 | 0,849 | 0,288 | 0,201 | 0,144 | 0,179 | +0,063 [+0,024; +0,101] | 7 / 1 / 2 |
| Logistic trên CLIP L/14 | 0,280 | 0,838 | 0,266 | 0,198 | 0,140 | 0,172 | +0,059 [+0,024; +0,095] | 6 / 3 / 1 |
| Logistic trên SigLIP B/16 | 0,339 | 0,832 | 0,261 | 0,201 | 0,137 | 0,164 | +0,059 [+0,022; +0,098] | 6 / 1 / 3 |
| **Logistic trên DINOv2 B/14** | **0,398** | **0,877** | **0,321** | **0,220** | **0,148** | **0,202** | **+0,082 [+0,043; +0,117]** | 6 / 3 / 1 |

Cột cuối đếm theo từng đường: số ảnh "Bị chặn" nằm trong top 20% của riêng đường đó, so với `occ_v2`. Hàng ngẫu nhiên là giá trị kỳ vọng, không phải số đo.

- **`lr_dinov2_b14` đạt quy tắc quyết định.** Hiệu tỉ lệ trúng ở top 20% là +0,082, khoảng tin cậy [+0,043; +0,117] nằm trên 0. Hiệu AP là +0,259 [+0,161; +0,358]. Top 20% (368 ảnh) chứa 81 ảnh "Bị chặn", so với 51 ảnh của `occ_v2` và khoảng 21 ảnh nếu bốc ngẫu nhiên.
- **Theo đường:** hơn `occ_v2` ở 6 đường, bằng ở 3, kém ở 1 (Nguyễn Kiệm#0: 6 so với 7 ảnh). Chỉ có 10 đường, nên số này chỉ cho thấy lợi thế không dồn vào một đường.
- **Cả bốn bộ logistic đều hơn `occ_v2`** với khoảng tin cậy nằm trên 0. Vì vậy kết luận "embedding + logistic hơn occupancy" không phụ thuộc vào việc chọn encoder. Việc chọn DINOv2 trong bốn encoder thì làm trên chính dữ liệu này, nên con số của riêng DINOv2 lạc quan một chút; khoảng tin cậy của bốn encoder chồng lên nhau.
- **Zero-shot không đạt quy tắc:** khoảng tin cậy của hiệu ở top 20% chứa 0 với cả ba encoder.
- **`occ_v2` không hơn `occ_v1`** trên nhãn người: hiệu top 20% của v1 so với v2 là +0,014 [−0,014; +0,041]. Các quy tắc thêm vào v2 sau khi nhìn tấm ảnh preview không được nhãn người ủng hộ. Việc số 18 trong [unresolved_items.md](unresolved_items.md) đóng ở đây.

**Vì sao bộ mới hơn** (cách giải thích, chưa có thí nghiệm tách riêng từng nguyên nhân): `occ_v2` chỉ đo lượng xe đậu trên vỉa hè theo 19 lớp của Cityscapes, nên không thấy sạp hàng, hàng hóa, bàn ghế, và cho 0 điểm với 60% số ảnh (chỉ 40% ảnh có `occ_v2` > 0), tức là không xếp hạng được phần lớn kho ảnh. Bộ mới học trực tiếp từ 1.989 nhãn người của train, nên học được cả các loại vật cản ngoài xe và cả việc ảnh nào sẽ bị gán "Không đủ thông tin". Hướng làm này (chủ động tìm mẫu dương của lớp hiếm bằng một model học từ nhãn đã có) theo Attenberg và Provost (2010) và Coleman và cộng sự (2022) trong danh sách dưới.

### Chọn theo điểm có giúp bộ phân loại không ([22_enrichment_simulation.py](../src/analysis/22_enrichment_simulation.py))

Mô phỏng trong train, 300 vòng: 4 đường làm nền, 3 đường làm "đường mới" (giấu nhãn), 3 đường để đánh giá. Mỗi vòng gán 20% kho của đường mới (trung bình 112 ảnh). Bộ phân loại là linear probe trên embedding DINOv2, **chỉ đọc chiều của khác biệt**. Kết quả: [enrichment_simulation.csv](../data/streets/enrichment_simulation.csv).

| Cách chọn | Ảnh "Bị chặn" trong 112 ảnh gán | Ảnh "Không đủ thông tin" | AP trên đường đánh giá | Hiệu AP so với ngẫu nhiên | Tỉ lệ vòng hơn ngẫu nhiên |
|---|---|---|---|---|---|
| Không bơm | | | 0,541 | −0,011 ± 0,004 | 40% |
| Ngẫu nhiên | 6,4 | 48,6 | 0,552 | | |
| Điểm cao nhất | 22,3 | 31,6 | 0,571 | +0,019 ± 0,005 | 68% |
| **70% điểm cao + 30% ngẫu nhiên** | 19,7 | 35,9 | 0,566 | +0,014 ± 0,005 | 65% |
| Uncertainty (điểm gần 0,5) | 17,5 | 33,9 | 0,569 | +0,017 ± 0,005 | 65% |
| Gán hết kho (560 ảnh) | 31,4 | 243,8 | 0,582 | +0,030 ± 0,005 | 74% |

- Chọn theo điểm cho khoảng **3 lần số ảnh "Bị chặn"** so với bốc ngẫu nhiên (19,7 so với 6,4 trên 112 ảnh), và ít ảnh "Không đủ thông tin" hơn (36 so với 49).
- Chiều của AP: mọi cách chọn theo điểm đều hơn ngẫu nhiên, và quy tắc 70/30 lấy được khoảng một nửa lợi ích của việc gán hết kho với 1/5 số nhãn. Khác biệt giữa "điểm cao nhất", 70/30 và uncertainty nằm trong sai số.
- Dấu ± là 1,96 sai số chuẩn qua 300 vòng. Các vòng dùng lại cùng 10 đường nên **khoảng này hẹp hơn thực tế**. Hiệu AP khoảng 0,01–0,02 là nhỏ; mô phỏng này không chứng minh được bơm ảnh sẽ cải thiện model fine-tune.

### Đòn bẩy: kho ứng viên lớn hơn

Với `lr_dinov2_b14`, tỉ lệ trúng tăng khi phần được chọn hẹp lại (tính từ bảng điểm, 1.839 ảnh):

| Phần kho được gán | Trúng (chỉ theo điểm) | Quy tắc 70/30 | Nếu gán 400 ảnh thì cần kho | Số ảnh "Bị chặn" kỳ vọng trong 400 ảnh (70/30) |
|---|---|---|---|---|
| 10% | 0,321 | 0,282 | 4.000 ảnh | khoảng 113 |
| 20% | 0,220 | 0,202 | 2.000 ảnh | khoảng 81 |
| 36% | 0,142 | 0,132 | 1.100 ảnh | khoảng 53 |

- Cột cuối là phép nhân từ số đo trên đường train cũ, **không phải số đo trên đường mới**. Đường mới được chọn vì điểm preview cao nên tỉ lệ nền có thể khác.
- Kho hiện tại của 10 đường đề xuất là 1.126 ảnh, tức 400 ảnh là 36% kho: vùng kém hiệu quả nhất của bảng. **Muốn tới khoảng 100 ảnh dương thì cần kho lớn hơn** (thêm đường, hoặc nới giới hạn 2 ngày chụp mỗi vị trí), chứ không phải chọn mạnh tay hơn trên kho nhỏ. Đây là việc nhóm cần quyết định.
- Chi phí chấm không còn là rào cản: trên RTX 5060, DINOv2 chấm 1.066 ảnh trong khoảng 16 giây (gồm cả nạp model), SegFormer-B5 mất 167 giây cho 1.839 ảnh. Trên CPU laptop: CLIP B/16 0,19 giây/ảnh, SegFormer-B5 khoảng 11 giây/ảnh. Thời gian chủ yếu là tải pano (1.127 pano trong 246 giây).

### Pipeline mới ([23_collect_train_extra.py](../src/collection/23_collect_train_extra.py))

1. Đọc đường từ [configs/streets_train_extra.yaml](../configs/streets_train_extra.yaml). File đang ở `status: proposed` với 10 đường ứng viên của mục 5; **việc chốt đường là của nhóm**. Script từ chối đường đã có trong `streets_v1.yaml` và đường trùng tên với đường val hoặc test, kể cả đoạn khác (đã thử: `Nguyễn Đình Chiểu#1` bị từ chối).
2. Vị trí cách nhau 25 m, tối đa 2 ngày chụp mỗi vị trí, cùng nhóm người chụp và năm chụp với bộ chính, trần 420 ảnh mỗi đường. Bỏ vị trí cách pano val hoặc test dưới 40 m (giao lộ với đường val/test; chỉ dùng tọa độ, không dùng nhãn) và vị trí đã có trong manifest.
3. Tải pano, lọc đêm, cắt ảnh theo `right_crop`, loại trùng tuyệt đối (md5) và gần trùng (dHash giữa hai ngày của cùng vị trí).
4. Chấm bằng bộ chọn ảnh fit trên **toàn bộ** 1.989 nhãn train (120 ảnh dương), C chọn bằng CV nhóm theo đường.
5. Chọn 400 ảnh: 280 theo điểm (mỗi đường tối đa 70 ảnh) và 120 ngẫu nhiên trong phần còn lại. Ghi `phase=train_extra`, `stratum`, `score`, `selector` vào manifest.

**Lượt chạy 11/11 (đề xuất, chưa dùng):**

- Kho: 1.127 pano trên 611 vị trí; bỏ 15 vị trí gần pano val/test và 3 vị trí đã dùng; 1 ảnh đêm; không có ảnh trùng. Còn 1.126 ảnh.
- Bộ chọn ảnh: `lr_dinov2_b14_C0.001`.
- Danh sách 400 ảnh: [train_extra_v1.csv](../data/manifest/train_extra_v1.csv), cột `streets_status = proposed`. Điểm của cả kho: [train_extra_v1_scores.csv](../data/streets/train_extra_v1_scores.csv).
- Theo đường (theo điểm + ngẫu nhiên): Lê Quang Định#0 42+11, Trần Xuân Soạn 40+20, Sư Vạn Hạnh 38+9, Hưng Phú 29+12, Ngô Quyền 26+15, Nguyễn Chí Thanh#0 25+11, Đinh Bộ Lĩnh 24+12, Bình Đông 19+12, Cao Thắng 19+11, Lê Đại Hành 18+7. Không đường nào chạm trần 70 ảnh.
- Tấm ảnh mẫu cho nhóm duyệt: [figures/train_extra_v1_sheet.jpg](figures/train_extra_v1_sheet.jpg), gồm 12 ảnh điểm cao nhất, 6 ảnh cuối tầng điểm (hạng 275–280) và 6 ảnh ngẫu nhiên. Quan sát của Claude, **không phải nhãn**: phần lớn 12 ảnh đầu là xe đậu, sạp hoặc hàng hóa trên vỉa hè; 6 ảnh cuối tầng điểm lẫn cả vỉa hè trống; trong đó có ảnh mà vỉa hè nằm trên vạch 3/5, có thể sẽ bị gán "Không đủ thông tin".

### Thay pipeline cũ

- Bỏ chế độ `--all` (chọn ảnh theo `occ_v2`) của script 16. Phần preview (`--dry`, `--sample`) giữ làm bản ghi của thử nghiệm 04/11.
- Script 17 chưa từng chạy và đã được script 21 thay thế; giữ file, có ghi chú ở đầu.
- `seg_measures.py` vẫn được script 16 và 21 dùng.

### Chưa kiểm chứng

- **Chưa có nhãn người nào trên đường mới.** Mọi tỉ lệ trúng ở trên đo trên 10 đường train cũ. Tỉ lệ trúng thật chỉ biết sau khi gán 400 ảnh; tầng ngẫu nhiên 30% cho phép đo lại điều này.
- Chỉ có 10 đường và 106 ảnh dương. Bootstrap lấy lại mẫu ảnh trong từng đường, không lấy lại mẫu đường, nên khoảng tin cậy chưa tính hết khác biệt giữa các đường.
- C được chọn là 0,001 ở gần như mọi lượt, tức là mép dưới của lưới (0,001–1). Lưới được giữ nguyên như đã đặt trước; regularization mạnh hơn có thể tốt hơn, chưa thử.
- Prompt zero-shot được đặt một lần và không chỉnh, nên kết quả zero-shot là của bộ prompt đó, không phải giới hạn của zero-shot.
- Ảnh train trên PC được dựng lại từ pano và `yaw` cho những ảnh còn thiếu (kiểm tra trên laptop: lệch 1,35–1,5 mức xám trên 5 ảnh do nén JPEG lại). Chưa đo ảnh hưởng của khác biệt này lên điểm.
- Linear probe trong script 22 không phải model fine-tune của đồ án.
- Bộ lọc gần trùng không tìm thấy cặp nào trong 1.126 ảnh; chưa xem bằng mắt để xác nhận.
- Dữ liệu chọn theo điểm lệch khỏi phân phối tự nhiên (Farquhar và cộng sự, 2021), nên EDA và báo cáo phải tách "main tự nhiên" và "train_extra".

### Chạy lại

```bash
pip install -r requirements.txt                                # PC có GPU: cài torch bản CUDA trước
python src/analysis/21_selector_benchmark.py --seg-n -1        # so bộ chấm; tự dựng lại ảnh train còn thiếu, cần MAPILLARY_TOKEN
python src/analysis/22_enrichment_simulation.py --enc dinov2_b14
python src/collection/23_collect_train_extra.py --dry          # đếm kho ứng viên, không tải
python src/collection/23_collect_train_extra.py --sample 60    # tập nhỏ, chỉ ra tấm ảnh mẫu
python src/collection/23_collect_train_extra.py --all          # cả kho, ghi manifest và tấm ảnh mẫu
```

### Việc tiếp theo (của nhóm)

1. Chốt danh sách đường trong `configs/streets_train_extra.yaml`, và quyết định có mở rộng kho không (bảng "Đòn bẩy").
2. Duyệt tấm ảnh mẫu. Chạy lại script 23 nếu danh sách đường đổi.
3. Sau đó mới trộn ảnh vào các project `MAIN_*` (mục 5, bước 5–6).

### Tài liệu tham khảo

Đã kiểm tra là có tồn tại. Cần đọc bản gốc trước khi trích nội dung vào báo cáo.

- Attenberg và Provost, "Why Label When You Can Search?", KDD 2010, [DOI 10.1145/1835804.1835859](https://doi.org/10.1145/1835804.1835859). Với lớp hiếm, chủ động đi tìm mẫu dương hiệu quả hơn active learning thuần.
- Garnett và cộng sự, "Bayesian Optimal Active Search and Surveying", ICML 2012, [arXiv:1206.6406](https://arxiv.org/abs/1206.6406). "Active search": mục tiêu là tìm càng nhiều mẫu dương càng tốt, khác với uncertainty sampling.
- Coleman và cộng sự, "Similarity Search for Efficient Active Learning and Search of Rare Concepts", AAAI 2022, [arXiv:2007.00077](https://arxiv.org/abs/2007.00077).
- Mullapudi và cộng sự, "Learning Rare Category Classifiers on a Tight Labeling Budget", [ICCV 2021](https://openaccess.thecvf.com/content/ICCV2021/html/Mullapudi_Learning_Rare_Category_Classifiers_on_a_Tight_Labeling_Budget_ICCV_2021_paper.html).
- Aggarwal, Popescu và Hudelot, "Active Learning for Imbalanced Datasets", [WACV 2020](https://openaccess.thecvf.com/content_WACV_2020/html/Aggarwal_Active_Learning_for_Imbalanced_Datasets_WACV_2020_paper.html).
- Farquhar, Gal và Rainforth, "On Statistical Bias in Active Learning: How and When to Fix It", ICLR 2021, [arXiv:2101.11665](https://arxiv.org/abs/2101.11665). Dữ liệu được chọn có chủ đích thì lệch khỏi phân phối gốc. Đây là lý do giữ 30% ảnh ngẫu nhiên và tách "main tự nhiên" với "train_extra" trong báo cáo.
- Hacohen, Dekel và Weinshall, "Active Learning on a Budget: Opposite Strategies Suit High and Low Budgets", ICML 2022, [arXiv:2202.02794](https://arxiv.org/abs/2202.02794).
- Oquab và cộng sự, "DINOv2: Learning Robust Visual Features without Supervision", [arXiv:2304.07193](https://arxiv.org/abs/2304.07193).

*Ảnh: © Mapillary contributors, CC BY-SA 4.0.*
