# Bơm thêm ảnh "Bị chặn" cho tập train

Ghi chép ngày 04/11/2026, cập nhật 11/11/2026. **Trạng thái: chưa bơm ảnh nào. Đang đo một bộ chọn ảnh mới (mục 7), chưa có kết quả.** Đã gán xong bộ chính, số ảnh "Bị chặn" thật thấp hơn ước tính (xem mục 1). Nhóm quyết định chờ gán xong đợt đầu rồi mới xem xét bơm thêm, và lấy ảnh từ **đường train mới**. Nhật ký kỹ thuật ở [collection_log.md](collection_log.md).

## Bàn giao (11/11/2026)

Đợt gán nhãn 1 đã xong, đây là đầu vào cho việc bơm ảnh:

- **Nhãn chính thức:** [data/labels/main_labels_v1.csv](../data/labels/main_labels_v1.csv), mỗi ảnh một dòng, gồm các cột `item`, `split`, `street_id`, `label` (0/1/I) và `source`. Ghép với [main_v1.csv](../data/manifest/main_v1.csv) (dòng `phase=main`) hoặc [pilot_v2.csv](../data/manifest/pilot_v2.csv) (dòng `phase=pilot`) theo `item` để lấy metadata Mapillary. Quy trình gán và phân xử: [labeling_phase1.md](labeling_phase1.md).
- **Bước 1 của mục 5 đã xong.** Số ảnh "Bị chặn" / số ảnh dùng được: train 120/1.132 (gồm 150 ảnh pilot, trong đó 14 ảnh Bị chặn), val 35/242, test 47/459.
- **Bắt đầu từ bước 2 của mục 5:** chọn đường train mới. Bộ chọn ảnh nên train trên nhãn train của file trên, lọc `split == "train"` và `label` thuộc {0, 1}.
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
- **Giới hạn từ gốc của cách này:** Cityscapes không có lớp xe đẩy, hàng hóa, bàn ghế, và occupancy đo lượng xe chứ không đo lối đi có liên tục hay không. Các quy tắc của v2 được đặt ra sau khi nhìn ảnh, nên **chưa được kiểm chứng**. Script 17 (so v1 và v2 trên phiếu pilot, bootstrap theo cặp) đã viết nhưng **chưa chạy**.
- SegFormer-B5 trên CPU laptop mất khoảng 6,7 giây mỗi ảnh. Toàn bộ 1.850 ảnh cần PC có GPU.

## 4. Quyết định

1. **Lấy ảnh từ đường train mới, không lấy thêm ngày khác ở đường cũ.** Ảnh cùng chỗ ít đa dạng (cùng mặt tiền, model dễ học thuộc nơi chốn), và các đường train cũ có thể ít bị lấn chiếm.
2. **Bơm sau đợt gán đầu.** Lúc đó biết chắc train và test thiếu ảnh dương tới đâu, và có nhãn người để xây bộ chọn ảnh tốt hơn.
3. **Bộ chọn ảnh ưu tiên:** đặc trưng CLIP hoặc DINOv2 cộng logistic regression, train trên nhãn train của đợt đầu (active learning). Trước khi dùng, so trên pilot với `occ_v1`, `occ_v2` và CLIP zero-shot, theo AUC và tỉ lệ trúng ở top 1/3, rồi chọn bộ tốt nhất.

## 5. Khi tiến hành

1. Đếm số ảnh "Bị chặn" thực tế của từng tập sau đợt gán đầu.
2. Chọn đường train mới. Ứng viên có điểm preview cao, chưa dùng ở đâu ([street_preview_v1b.csv](../data/streets/street_preview_v1b.csv); điểm theo đường chỉ là gợi ý, sai số khoảng ±20 điểm %): Cao Thắng 0,53 · Hưng Phú 0,45 · Lê Quang Định#0 0,45 (Chợ Bà Chiểu) · Trần Xuân Soạn 0,40 · Đinh Bộ Lĩnh 0,35 · Nguyễn Chí Thanh#0 0,35 · Ngô Quyền 0,30 (Chợ Nhật Tảo) · Sư Vạn Hạnh 0,30 · Bình Đông 0,30 · Lê Đại Hành 0,30.
   - **Không dùng đoạn khác của đường val hoặc test**, ví dụ Nguyễn Đình Chiểu#1, để giữ đúng câu hỏi "đường chưa thấy".
   - Ghi đường mới vào `configs/streets_v1.yaml` với `split: train`.
3. Chạy lại 01–03 trên PC để ghép pano với đường mới. Bước 02 quét toàn khu vực, khoảng 30 phút. Viết script thu thập dựa trên `11_collect_main.py` (vị trí 25 m, ≤2 lượt mỗi vị trí), cộng phần chấm điểm, lưu cache và chọn theo tầng từ script 16.
4. Chọn khoảng 400 ảnh: khoảng 70% theo điểm, mỗi đường tối đa 25% phần này, cộng khoảng 30% ngẫu nhiên. Ghi `phase=train_extra` và `stratum` vào manifest.
5. Cho cả nhóm xem trước một tấm ảnh mẫu, rồi mới trộn ảnh vào các project `MAIN_*`. Người gán không biết ảnh nào là ảnh bơm.
6. Trong EDA và báo cáo, tách số liệu "main tự nhiên" và "train_extra" riêng.

## 6. Chạy lại thử nghiệm

```bash
python src/analysis/16_train_extra_preview.py --dry          # đếm kho ứng viên, cần MAPILLARY_TOKEN
python src/analysis/16_train_extra_preview.py --sample 80    # tập nhỏ, tấm ảnh ở data/crops/train_extra_sheet.jpg
python src/analysis/17_check_scorer_pilot.py                 # so occ_v1 và occ_v2 trên phiếu pilot (nên chạy trên GPU)
```

Ảnh, mask và metadata được lưu trong `data/raw/` và `data/crops/`, không đưa lên git. Bảng điểm của tập nhỏ: [train_extra_preview_scores.csv](../data/streets/train_extra_preview_scores.csv).

## 7. Bộ chọn ảnh mới: đang đo (11/11/2026)

**Trạng thái: code đã viết, chưa chạy, chưa có kết quả.** Pipeline cũ (mục 3) vẫn là pipeline hiện hành cho tới khi có số đo. Nhánh `enrichment-selector`.

### Đã có

| File | Việc |
|---|---|
| [src/enrich.py](../src/enrich.py) | Tải pano, dựng lại ảnh cắt từ `yaw` trong manifest, embedding đóng băng (CLIP ViT-B/16, CLIP ViT-L/14, DINOv2 ViT-B/14, SigLIP B/16), bộ chọn ảnh = logistic regression P(Bị chặn) trên embedding |
| [21_selector_benchmark.py](../src/analysis/21_selector_benchmark.py) | So `occ_v1`, `occ_v2`, zero-shot và logistic trên từng encoder bằng nhãn người của train. Thay cho script 17 (17 chỉ so v1 và v2 trên 150 ảnh pilot) |
| [22_enrichment_simulation.py](../src/analysis/22_enrichment_simulation.py) | Mô phỏng trong train: chọn ảnh theo điểm có giúp bộ phân loại không, hay chỉ tăng số ảnh dương |

Hai script 21 và 22 mới qua kiểm tra cú pháp, **chưa chạy lần nào**.

### Cách đo

- **Chỉ dùng nhãn train.** Không đọc nhãn val và test, kể cả để chọn encoder.
- **Giữ nguyên một đường ra ngoài:** ảnh của mỗi đường được chấm bởi model chỉ thấy 9 đường train còn lại, giống tình huống thật là chấm ảnh của đường mới.
- **Mục tiêu:** 1 nếu "Bị chặn", 0 cho cả "Còn lối đi" lẫn "Không đủ thông tin". Tỉ lệ trúng khi đó là số ảnh "Bị chặn" trên mỗi ảnh người phải gán.
- **Đo trên 1.839 ảnh main của train** (phân phối tự nhiên, 106 ảnh dương). 150 ảnh pilot chỉ dùng để fit, vì được lấy mẫu lệch.
- **Chỉ số:** AP, AUC, tỉ lệ trúng ở top 10% / 20% / 33%, và mô phỏng quy tắc của mục 5 (70% theo điểm, trần 25% mỗi đường, 30% ngẫu nhiên). Khoảng tin cậy bằng bootstrap theo cặp so với `occ_v2`.
- **Quy tắc quyết định, đặt trước khi xem số:** thay pipeline cũ chỉ khi bộ mới hơn `occ_v2` về tỉ lệ trúng ở top 20% (khoảng tin cậy 95% của hiệu nằm trên 0) và không kém về AP. So nhiều encoder trên cùng dữ liệu thì bộ thắng bị lạc quan một chút.

### Số đã đo trên laptop (không GPU)

- Máy laptop chỉ có 303/2.999 ảnh cắt của bộ chính. Ảnh dựng lại từ pano và `yaw` khớp ảnh gốc: 5 ảnh kiểm tra lệch trung bình 1,35–1,5 mức xám, do nén JPEG lại. Đã dựng lại đủ 1.839 ảnh train.
- Tải 1.518 pano mất 890 giây với 8 luồng. Mapillary có lúc bóp tốc độ tới khoảng 11 giây mỗi yêu cầu.
- SegFormer-B5 khoảng 11 giây/ảnh trên CPU (đo lúc máy đang tải ảnh). CLIP ViT-B/16 khoảng 0,19 giây/ảnh (1.851 ảnh trong 355 giây). Bộ chấm embedding rẻ hơn khoảng 50 lần, nên có thể chấm kho ứng viên lớn hơn. Chất lượng thì **chưa đo**.

### Việc còn lại (chạy trên PC có GPU)

```bash
pip install -r requirements.txt                              # thêm scikit-learn, sentencepiece, protobuf
python src/analysis/21_selector_benchmark.py --seg-n -1      # tự dựng lại ảnh train còn thiếu; cần MAPILLARY_TOKEN
python src/analysis/22_enrichment_simulation.py --enc <encoder thắng>
```

1. Chạy hai lệnh trên, sửa lỗi nếu có, ghi bảng kết quả vào mục này.
2. Nếu bộ mới thắng theo quy tắc trên: viết script thu thập cho đường train mới (mục 5, bước 3–4) dùng bộ chọn ảnh này, và bỏ phần chọn ảnh `--all` của script 16. Nếu không thắng thì giữ pipeline cũ và ghi lại kết quả.
3. Danh sách đường mới để ở file riêng, trạng thái "đề xuất". Việc chốt đường là của nhóm.

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
