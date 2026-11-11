# Bơm thêm ảnh "Bị chặn" cho tập train

Ghi chép ngày 04/11/2026, cập nhật 11/11/2026. **Trạng thái: chưa bơm ảnh nào. Bộ chọn ảnh mới (embedding DINOv2 + logistic) đã đo xong và thay bộ chấm `occ_v2` (mục 7). Đã quét 150 đường để chọn đường (mục 8) và lập danh sách 2.000 ảnh từ 75 đường, chia 400 ảnh cho mỗi người gán (mục 9). **Đã đưa lên Label Studio ngày 11/11: 5 project `MAIN2_<tên>`, mỗi project 400 ảnh, chưa ai gán.** Đã gán xong bộ chính, số ảnh "Bị chặn" thật thấp hơn ước tính (xem mục 1). Nhóm quyết định chờ gán xong đợt đầu rồi mới xem xét bơm thêm, và lấy ảnh từ **đường train mới**. Nhật ký kỹ thuật ở [collection_log.md](collection_log.md).

## Bàn giao (11/11/2026)

Đợt gán nhãn 1 đã xong, đây là đầu vào cho việc bơm ảnh:

- **Nhãn chính thức:** [data/labels/main_labels_v1.csv](../data/labels/main_labels_v1.csv), mỗi ảnh một dòng, gồm các cột `item`, `split`, `street_id`, `label` (0/1/I) và `source`. Ghép với [main_v1.csv](../data/manifest/main_v1.csv) (dòng `phase=main`) hoặc [pilot_v2.csv](../data/manifest/pilot_v2.csv) (dòng `phase=pilot`) theo `item` để lấy metadata Mapillary. Quy trình gán và phân xử: [labeling_phase1.md](labeling_phase1.md).
- **Bước 1 của mục 5 đã xong.** Số ảnh "Bị chặn" / số ảnh dùng được: train 120/1.132 (gồm 150 ảnh pilot, trong đó 14 ảnh Bị chặn), val 35/242, test 47/459.
- **Bước 2–4 của mục 5 đã làm** (mục 7–9): 75 đường từ lượt quét và 2.000 ảnh (Phúc chốt số lượng 11/11), đã lên Label Studio, chờ gán. Bộ chọn ảnh train trên mọi nhãn train của file trên (`split == "train"`), với mục tiêu "Bị chặn" so với phần còn lại, gồm cả "Không đủ thông tin".
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
4. Chọn ảnh (kế hoạch 04/11 là khoảng 400 ảnh; ngày 11/11 chốt 2.000 ảnh, xem mục 9): khoảng 70% theo điểm, mỗi đường tối đa 25% phần này, cộng khoảng 30% ngẫu nhiên. Ghi `phase=train_extra` và `stratum` vào manifest.
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
- Kho của 10 đường đề xuất ban đầu là 1.126 ảnh, tức 400 ảnh là 36% kho: vùng kém hiệu quả nhất của bảng. **Muốn nhiều ảnh dương hơn thì cần kho lớn hơn**, chứ không phải chọn mạnh tay hơn trên kho nhỏ. Vì vậy có lượt quét đường (mục 8) và danh sách 75 đường (mục 9).
- Chi phí chấm không còn là rào cản: trên RTX 5060, DINOv2 chấm 1.066 ảnh trong khoảng 16 giây (gồm cả nạp model), SegFormer-B5 mất 167 giây cho 1.839 ảnh. Trên CPU laptop: CLIP B/16 0,19 giây/ảnh, SegFormer-B5 khoảng 11 giây/ảnh. Thời gian chủ yếu là tải pano (1.127 pano trong 246 giây).

### Pipeline mới ([23_collect_train_extra.py](../src/collection/23_collect_train_extra.py))

1. Đọc đường từ [configs/streets_train_extra.yaml](../configs/streets_train_extra.yaml). File hiện có 75 đường từ lượt quét (mục 8), `status: approved`. Script từ chối đường đã có trong `streets_v1.yaml` và đường trùng tên với đường val hoặc test, kể cả đoạn khác (đã thử: `Nguyễn Đình Chiểu#1` bị từ chối).
2. Vị trí cách nhau 25 m, tối đa 2 ngày chụp mỗi vị trí, cùng nhóm người chụp và năm chụp với bộ chính, trần 420 ảnh mỗi đường. Bỏ vị trí cách pano val hoặc test dưới 40 m (giao lộ với đường val/test; chỉ dùng tọa độ, không dùng nhãn) và vị trí đã có trong manifest.
3. Tải pano, lọc đêm, cắt ảnh theo `right_crop`, loại trùng tuyệt đối (md5) và gần trùng (dHash giữa hai ngày của cùng vị trí).
4. Chấm bằng bộ chọn ảnh fit trên **toàn bộ** 1.989 nhãn train (120 ảnh dương), C chọn bằng CV nhóm theo đường.
5. Chọn `--n` ảnh (mặc định 2.000): 70% theo điểm (mỗi đường tối đa 25% phần này) và 30% ngẫu nhiên trong phần còn lại. Ghi `phase=train_extra`, `stratum`, `score`, `selector` vào manifest, và chia đều ngẫu nhiên cho 5 người gán của đợt chính (`train_extra_v1_assignment.csv`).

**Lượt chạy đầu (11/11, đã bị thay):** 10 đường ứng viên của mục 5, kho 1.126 ảnh, chọn 400 ảnh (280 theo điểm + 120 ngẫu nhiên). Lượt quét đường (mục 8) cho thấy 10 đường này chỉ xếp hạng 34–103 trên 150, nên danh sách đó được thay bằng danh sách của mục 9. Các file `train_extra_v1*` hiện là của mục 9.

### Thay pipeline cũ

- Bỏ chế độ `--all` (chọn ảnh theo `occ_v2`) của script 16. Phần preview (`--dry`, `--sample`) giữ làm bản ghi của thử nghiệm 04/11.
- Script 17 chưa từng chạy và đã được script 21 thay thế; giữ file, có ghi chú ở đầu.
- `seg_measures.py` vẫn được script 16 và 21 dùng.

### Chưa kiểm chứng

- **Chưa có nhãn người nào trên đường mới.** Mọi tỉ lệ trúng ở trên đo trên 10 đường train cũ. Tỉ lệ trúng thật chỉ biết sau khi gán 2.000 ảnh; tầng ngẫu nhiên 30% cho phép đo lại điều này.
- Chỉ có 10 đường và 106 ảnh dương. Bootstrap lấy lại mẫu ảnh trong từng đường, không lấy lại mẫu đường, nên khoảng tin cậy chưa tính hết khác biệt giữa các đường.
- C được chọn là 0,001 ở gần như mọi lượt, tức là mép dưới của lưới (0,001–1). Lưới được giữ nguyên như đã đặt trước; regularization mạnh hơn có thể tốt hơn, chưa thử.
- Prompt zero-shot được đặt một lần và không chỉnh, nên kết quả zero-shot là của bộ prompt đó, không phải giới hạn của zero-shot.
- Ảnh train trên PC được dựng lại từ pano và `yaw` cho những ảnh còn thiếu (kiểm tra trên laptop: lệch 1,35–1,5 mức xám trên 5 ảnh do nén JPEG lại). Chưa đo ảnh hưởng của khác biệt này lên điểm.
- Linear probe trong script 22 không phải model fine-tune của đồ án.
- Bộ lọc gần trùng chỉ tìm thấy 1 cặp trong 5.036 ảnh (mục 9); chưa xem bằng mắt để xác nhận là không sót.
- Dữ liệu chọn theo điểm lệch khỏi phân phối tự nhiên (Farquhar và cộng sự, 2021), nên EDA và báo cáo phải tách "main tự nhiên" và "train_extra".

### Chạy lại

```bash
pip install -r requirements.txt                                # PC có GPU: cài torch bản CUDA trước
python src/analysis/21_selector_benchmark.py --seg-n -1        # so bộ chấm; tự dựng lại ảnh train còn thiếu, cần MAPILLARY_TOKEN
python src/analysis/22_enrichment_simulation.py --enc dinov2_b14
python src/collection/23_collect_train_extra.py --dry          # đếm kho ứng viên, không tải
python src/collection/23_collect_train_extra.py --sample 60    # tập nhỏ, chỉ ra tấm ảnh mẫu
python src/collection/23_collect_train_extra.py --all          # cả kho; ghi manifest, phân công và tấm ảnh mẫu (--n 2000 mặc định)
```

### Việc tiếp theo

Xem mục 9.

## 8. Quét đường: đường nào có nhiều ảnh "Bị chặn" nhất (11/11/2026)

Script: [24_street_scan.py](../src/analysis/24_street_scan.py). Bảng: [street_scan_v1.csv](../data/streets/street_scan_v1.csv) (150 đường), điểm từng ảnh: [street_scan_v1_crops.csv](../data/streets/street_scan_v1_crops.csv). Ảnh: [figures/street_scan_v1_sheet.jpg](figures/street_scan_v1_sheet.jpg). **Điểm của đường chỉ để chọn đường, không phải nhãn.**

### Cách làm

- 150 đường có từ 30 vị trí trở lên, chưa dùng trong `streets_v1.yaml`, không trùng tên đường val hoặc test. Mỗi đường lấy 30 ô lưới 25 m ngẫu nhiên, mỗi ô một pano. 4.500 pano, bỏ 100 ảnh đêm, còn 4.400 ảnh.
- Chấm bằng bộ chọn ảnh của mục 7 (`lr_dinov2_b14_C0.001`, fit trên toàn bộ nhãn train). Điểm của đường là trung bình điểm 30 ảnh, kèm khoảng tin cậy 95% bằng bootstrap.
- **Kiểm tra trước trên 10 đường train:** điểm trung bình của đường (chấm khi model chưa thấy đường đó) xếp hạng gần trùng với tỉ lệ "Bị chặn" thật: Spearman 0,96. Điểm preview cũ (`street_preview_v1b.csv`, bằng model PoC) chỉ đạt 0,40 trên cùng 10 đường.
- `est_blocked` đổi điểm trung bình thành tỉ lệ "Bị chặn" bằng một đường thẳng fit trên 10 đường train (tỉ lệ ≈ −0,012 + 0,353 × điểm). Chỉ có 10 điểm và điểm cao nhất của train là 0,43, nên với đường có điểm trên 0,43 đây là **ngoại suy**.

### Kết quả

Tỉ lệ "Bị chặn" thật của train để so: cao nhất là Hải Thượng Lãn Ông 17% (điểm 0,43), trung bình 5,8%.

| Hạng | Đường | Điểm TB [95%] | Ước lượng "Bị chặn" | Vị trí 25 m | Loại đường | Chợ gần |
|---|---|---|---|---|---|---|
| 1 | Phạm Hữu Chí#0 | 0,67 [0,55; 0,78] | 22% | 30 | residential | |
| 2 | Nhật Tảo | 0,66 [0,55; 0,77] | 22% | 51 | residential | Chợ Nhật Tảo |
| 3 | Tôn Đản | 0,66 [0,57; 0,75] | 22% | 34 | tertiary | Chợ Long Kiểng |
| 4 | Thích Quảng Đức | 0,66 [0,58; 0,74] | 22% | 30 | tertiary | |
| 5 | Hoàng Hoa Thám | 0,64 [0,53; 0,74] | 21% | 51 | tertiary | Chợ Cây Quéo |
| 6 | Phan Văn Hân | 0,63 [0,52; 0,73] | 21% | 33 | residential | Chợ Thị Nghè |
| 7 | Nguyễn Thượng Hiền#1 | 0,62 [0,53; 0,71] | 21% | 36 | tertiary | Chợ Vườn Chuối |
| 8 | Nguyễn Thượng Hiền#0 | 0,60 [0,48; 0,71] | 20% | 59 | residential | Chợ Cây Quéo |
| 9 | Trần Quý | 0,59 [0,48; 0,69] | 20% | 30 | tertiary | Chợ Thiếc |
| 10 | Lạc Long Quân | 0,59 [0,49; 0,68] | 19% | 43 | secondary | |
| 11 | Vạn Kiếp#0 | 0,57 [0,48; 0,66] | 19% | 30 | tertiary | |
| 12 | Đỗ Ngọc Thạnh | 0,55 [0,46; 0,65] | 18% | 33 | tertiary | Chợ Kim Biên |
| 13 | Chu Văn An#0 | 0,53 [0,41; 0,65] | 17% | 30 | tertiary | Chợ Cây Điệp |
| 14 | Ung Văn Khiêm | 0,53 [0,41; 0,64] | 17% | 68 | secondary | |
| 15 | Vĩnh Khánh | 0,53 [0,41; 0,65] | 17% | 41 | tertiary | |
| 16 | Bùi Thị Xuân#0 | 0,52 [0,42; 0,63] | 17% | 34 | residential | |
| 17 | Phan Văn Trị#0 | 0,52 [0,42; 0,62] | 17% | 41 | tertiary | Chợ Cây Điệp |
| 18 | Nguyễn Thái Bình#0 | 0,52 [0,42; 0,61] | 17% | 49 | tertiary | |
| 19 | Bà Hạt | 0,51 [0,40; 0,63] | 17% | 45 | tertiary | Chợ Nhật Tảo |
| 20 | Ba Đình#1 | 0,51 [0,40; 0,62] | 17% | 35 | tertiary | Chợ Ba Đình |

Đường lớn (primary, secondary) có điểm cao nhất: Lạc Long Quân (hạng 10), Ung Văn Khiêm (14), Bạch Đằng#0 (26; 0,48), Lê Hồng Phong#1 (28; 0,47), Phan Đình Phùng (30; 0,46), Tùng Thiện Vương (32; 0,44).

**10 đường đề xuất cũ của mục 5 xếp hạng 34–103 trên 150:** Nguyễn Chí Thanh#0 34 (0,42), Đinh Bộ Lĩnh 38 (0,41), Lê Quang Định#0 39 (0,41), Sư Vạn Hạnh 42 (0,40), Ngô Quyền 53 (0,37), Bình Đông 71 (0,29), Cao Thắng 78 (0,26), Trần Xuân Soạn 79 (0,24), Hưng Phú 81 (0,23), Lê Đại Hành 103 (0,17). Điểm trung bình của cả 10 đường là 0,32 (ước lượng khoảng 10% "Bị chặn"), còn 20 đường đầu bảng khoảng 0,58 (ước lượng 19%).

### Cách đọc và giới hạn

- **Đường điểm cao hầu hết là đường nhỏ gần chợ** (tertiary, residential: điểm trung bình 0,34 và 0,37; primary 0,21, secondary 0,24). 10 đường train và các đường val, test đều là đường lớn. Bộ chọn ảnh chưa từng được kiểm chứng trên đường nhỏ, và ảnh dương từ đường nhỏ gần chợ có thể khác kiểu với ảnh dương ở val/test. Đường nhỏ cũng có thể có nhiều ảnh "Không đủ thông tin" hơn (vỉa hè hẹp hoặc không có), dù mục tiêu của bộ chọn ảnh đã tính các ảnh này là âm.
- **Đầu bảng bị lạc quan:** xếp hạng 150 đường theo trung bình của 30 ảnh thì đường đứng đầu một phần là do may. Khoảng tin cậy của một đường rộng khoảng ±0,10.
- **Đường điểm cao thì ngắn:** 20 đường đầu có tổng 803 vị trí (10 đường đề xuất cũ: 748). Muốn kho khoảng 2.000 ảnh với ≤2 ngày mỗi vị trí thì cần khoảng 25–30 đường đầu bảng.
- Quan sát của Claude trên tấm ảnh (không phải nhãn): các đường đầu bảng có nhiều sạp hàng, hàng hóa và xe đậu trên vỉa hè; cũng có ảnh vỉa hè trống trước cửa cuốn đóng và ảnh hẻm hẹp khó thấy vỉa hè.
- Chưa có nhãn người trên bất kỳ đường nào trong bảng này.

### Đã dùng kết quả này

Danh sách đường của `configs/streets_train_extra.yaml` được thay bằng 75 đường đầu bảng (mục 9).

```bash
python src/analysis/24_street_scan.py        # khoảng 15 phút tải 4.500 pano, chấm trên GPU
```

## 9. Danh sách bơm: 2.000 ảnh từ 75 đường (11/11/2026)

**Quyết định của Phúc (11/11):** gán một đợt duy nhất vì không còn thời gian, 2.000 ảnh, mỗi người 400 ảnh, mỗi ảnh một người gán, và đưa lên Label Studio ngay (không chờ buổi xem tấm ảnh mẫu như kế hoạch ở mục 5).

### Đường

- [configs/streets_train_extra.yaml](../configs/streets_train_extra.yaml): 75 đường có điểm quét cao nhất trong 150 đường (điểm trung bình từ 0,275 trở lên, tức nửa trên của bảng mục 8). Gồm 23 đường lớn (10 primary, 13 secondary) và 52 đường nhỏ (44 tertiary, 8 residential). 6 trong 10 đường ứng viên cũ còn trong danh sách.
- Vì sao 75 đường: kho phải đủ lớn để 2.000 ảnh vẫn là chọn lọc. Đếm bằng `--dry`: 50 đường cho 3.137 ảnh (2.000 ảnh là 64% kho), 75 đường cho 5.074 ảnh (39%), 100 đường cho 7.511 ảnh (27%). Từ đường thứ 76 trở xuống điểm quét thấp hơn mức của phần lớn đường train cũ.
- `status` đã đổi thành `approved` (Phúc chốt 11/11). `streets_v1.yaml` chưa đổi: 75 đường này chỉ có ảnh `train_extra`, không thuộc bộ chính.

### Lượt chạy

```bash
python src/collection/23_collect_train_extra.py --all --n 2000
```

- Kho: 5.074 pano trên 3.077 vị trí. Bỏ 57 vị trí cách pano val/test dưới 40 m và 37 vị trí đã dùng. Sau khi tải: 38 ảnh đêm, 1 ảnh gần trùng, còn **5.035 ảnh**. Tải mất 911 giây, chấm 54 giây.
- Bộ chọn ảnh: `lr_dinov2_b14_C0.001`, fit trên 1.989 ảnh train (120 ảnh dương).
- Chọn **2.000 ảnh** (40% kho): 1.400 theo điểm (điểm từ 0,61 trở lên, trung bình 0,80) và 600 ngẫu nhiên trong phần còn lại (điểm trung bình 0,23). Trần mỗi đường của tầng điểm là 350 ảnh; đường nhiều nhất có 101 ảnh.
- Theo loại đường (theo điểm + ngẫu nhiên): tertiary 846 + 384, secondary 266 + 108, residential 151 + 38, primary 137 + 70. Tức 581 ảnh (29%) từ đường lớn.
- Đường nhiều ảnh nhất: Hoàng Sa 157, Trường Sa#0 117 (hai đường dài ven kênh, cộng lại 14% danh sách), Lê Quang Định#0 52, Nguyễn Chí Thanh#0 47, Nguyễn Thượng Hiền#0 47. Đường ít nhất có 6 ảnh.

### File

| File | Nội dung |
|---|---|
| [train_extra_v1.csv](../data/manifest/train_extra_v1.csv) | 2.000 ảnh: nguồn gốc, `phase=train_extra`, `stratum` (`top_score` hoặc `random`), `score`, `selector`, `streets_status` |
| [train_extra_v1_assignment.csv](../data/manifest/train_extra_v1_assignment.csv) | Phân công: Học, Khải, Loan, Minh, Phúc mỗi người 400 ảnh, chia ngẫu nhiên, `role=train_extra_single`. Người gán không biết tầng của ảnh |
| [train_extra_v1_scores.csv](../data/streets/train_extra_v1_scores.csv) | Điểm và trạng thái của cả kho 5.074 pano |
| [figures/train_extra_v1_sheet.jpg](figures/train_extra_v1_sheet.jpg) | Tấm ảnh mẫu: 12 ảnh điểm cao nhất, 6 ảnh cuối tầng điểm (hạng 1.395–1.400), 6 ảnh ngẫu nhiên |

Ảnh cắt nằm ở `data/crops/train_extra_v1/` (không đưa lên git); dựng lại bằng lệnh trên.

Quan sát của Claude trên tấm ảnh mẫu, **không phải nhãn**: 12 ảnh điểm cao nhất đều là sạp hàng, hàng hóa hoặc xe đậu kín vỉa hè, phần lớn ở đường nhỏ gần chợ. 6 ảnh cuối tầng điểm (điểm 0,61) lẫn lộn: có ảnh vỉa hè còn lối đi và ảnh xe sát camera. 6 ảnh ngẫu nhiên phần lớn là vỉa hè trống hoặc không thấy rõ vỉa hè.

### Cần biết khi dùng

- **Chưa biết sẽ thu được bao nhiêu ảnh "Bị chặn".** Nếu đường mới giống 10 đường train cũ thì quy tắc 70/30 ở mức 36–40% kho cho khoảng 12–13% ảnh dương, tức khoảng 250 ảnh. Điểm quét của 75 đường này cao hơn đường train cũ nên con số có thể cao hơn, nhưng đó là ngoại suy.
- **Ảnh bơm nhiều hơn phần train tự nhiên** (2.000 so với 1.839 ảnh main). Cột `stratum` và `phase` cho phép lấy bớt ảnh bơm lúc train nếu train bị lệch.
- **71% ảnh bơm đến từ đường nhỏ**, trong khi train, val và test của bộ chính đều là đường lớn. Bộ chọn ảnh chưa được kiểm chứng trên đường nhỏ, và ảnh dương ở đó có thể khác kiểu với val/test.
- **Mỗi ảnh một người gán**, nên phần bơm không có số đồng thuận. Muốn có thì cho khoảng 100 ảnh được hai người gán.
- **Nếu dùng DINOv2 làm một model so sánh:** ảnh bơm được chọn bằng chính đặc trưng DINOv2, có thể hơi thuận lợi cho nó. Nên chạy thêm một lượt chỉ với "main tự nhiên" để so.
- 30% ảnh ngẫu nhiên cho phép đo tỉ lệ trúng thật của bộ chọn ảnh trên đường mới sau khi gán: so tỉ lệ "Bị chặn" của `top_score` với `random`.

### Trên Label Studio (11/11)

Script: [25_ls_create_train_extra.py](../src/labeling/25_ls_create_train_extra.py) (mặc định chạy thử, `--apply` mới tạo project).

- 2.000 ảnh được chép lên server vào `/srv/sidewalk/data/crops/train_extra_v1` (201 MB; md5 của 3 ảnh khớp bản trên PC).
- 5 project mới `MAIN2_Hoc`, `MAIN2_Khai`, `MAIN2_Loan`, `MAIN2_Minh`, `MAIN2_Phuc`, mỗi project 400 ảnh theo file phân công, thứ tự ngẫu nhiên riêng. Giao diện v1 và guide v1, giống `MAIN_*`.
- Tách project riêng thay vì trộn vào `MAIN_*` (kế hoạch ở mục 5): các project `MAIN_*` đã gán xong và là bản ghi của đợt 1, và `19_main_agreement.py` đọc mọi project `MAIN_*`. Mỗi task chỉ chứa ảnh và mã `item`; không có tầng, điểm hay tên đường.
- Đã kiểm tra: 5 project có 400 task, chưa có nhãn; 60 ảnh thử ngẫu nhiên đều hiển thị được; danh sách task của `MAIN2_Phuc` khớp file phân công; 5 project `MAIN_*` vẫn 887/887.

### Việc tiếp theo

1. Mỗi người gán 400 ảnh trong project `MAIN2_<tên>` của mình, theo [guide v1](../labeling/guide/annotation_guide_v1_draft.md).
2. Sau khi gán: kéo nhãn về (chưa có script; `19_main_agreement.py` chỉ đọc `MAIN_*`), so tỉ lệ "Bị chặn" của tầng `top_score` với `random`, gộp nhãn vào file nhãn chính với `phase=train_extra`.
3. Tách "main tự nhiên" với "train_extra" trong EDA và báo cáo.

## Tài liệu tham khảo

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
