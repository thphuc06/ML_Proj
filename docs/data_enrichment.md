# Bơm thêm ảnh "Bị chặn" cho tập train

Ghi chép ngày 04/11/2026. **Trạng thái: mới thăm dò, chưa bơm ảnh nào.** Nhóm quyết định chờ gán xong đợt đầu rồi mới xem xét bơm thêm, và lấy ảnh từ **đường train mới**. Nhật ký kỹ thuật ở [collection_log.md](collection_log.md).

## 1. Vấn đề

Lớp "Bị chặn" hiếm, nên có thể không đủ ảnh để train và đánh giá. Hiện **chưa ai đo trên bộ chính**. Các số dưới đây là ước lượng, nhân từ ba nguồn:

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

*Ảnh: © Mapillary contributors, CC BY-SA 4.0.*
