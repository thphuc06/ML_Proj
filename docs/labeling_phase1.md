# Gán nhãn đợt 1: quy trình và kết quả

Tổng kết ngày 11/11/2026, dùng cho phần dữ liệu của báo cáo. Nhãn cuối: [data/labels/main_labels_v1.csv](../data/labels/main_labels_v1.csv). Số liệu chi tiết: [main_report.md](../data/labels/main_report/main_report.md). Nhật ký kỹ thuật: [collection_log.md](collection_log.md).

## 1. Tóm tắt

- **2.999 ảnh**, chụp từ Mapillary trên 17 tuyến đường. Mỗi ảnh nhìn vỉa hè bên phải xe chụp.
- **5 người gán**, mỗi người 887 lượt, tổng cộng 4.435 lượt. Không thiếu lượt nào.
- **Đồng thuận (Cohen κ, 3 nhãn):** test 0,60 · val 0,64 · train gán chéo 0,61. Cả ba đều đạt ngưỡng 0,6 của đề cương. Pilot trước đó chỉ đạt 0,57.
- **303 ảnh bất đồng** được phân xử. Claude đề xuất nhãn bằng cách xem ảnh, Khải duyệt và sửa 28 ảnh.
- **150 ảnh pilot** (3 đường train) được xem lại toàn bộ theo guide v1 và đưa vào train. Phúc sửa 3 ảnh.
- **Kết quả:** 3.149 ảnh có nhãn cuối. 1.833 ảnh dùng được, gồm 1.631 ảnh "Còn lối đi" và 202 ảnh "Bị chặn". 1.316 ảnh "Không đủ thông tin" bị loại khỏi model.

| Tập | Còn lối đi (0) | Bị chặn (1) | Dùng được | Tỉ lệ Bị chặn | Không đủ thông tin |
|---|---|---|---|---|---|
| Train (bộ chính) | 939 | 106 | 1.045 | 10,1% | 794 |
| Train (pilot) | 73 | 14 | 87 | 16,1% | 63 |
| **Train, cộng** | **1.012** | **120** | **1.132** | **10,6%** | **857** |
| Val | 207 | 35 | 242 | 14,5% | 244 |
| Test | 412 | 47 | 459 | 10,2% | 215 |
| **Tổng** | **1.631** | **202** | **1.833** | **11,0%** | **1.316** |

Ảnh pilot được lấy mẫu nghiêng về phía ảnh trông như bị chặn, nên tỉ lệ "Bị chặn" của pilot cao hơn. Khi làm EDA cần tách riêng theo cột `phase`.

## 2. Quy trình

| Bước | Việc | Kết quả |
|---|---|---|
| 1. Pilot | 5 người gán độc lập cùng 150 ảnh theo guide v0 | Fleiss κ 0,57, chưa đạt 0,6. Ranh giới khó nhất là xe máy đậu và vỉa hè ở xa ([báo cáo pilot](../data/labels/pilot_report/pilot_report_20261029_0903.md)) |
| 2. Rà soát pilot | Đo từng quy tắc trên phiếu pilot, gộp hai lý do "không thấy vỉa hè" | Viết [guide v1](../labeling/guide/annotation_guide_v1_draft.md) (quy tắc vạch 3/5) và [bảng tra nhanh](../labeling/guide/bang_tra_nhanh.jpg) |
| 3. Chốt guide | Phúc xác nhận dùng guide v1 nguyên văn, kể cả các đề xuất "(chờ họp)" | Xem quy tắc ở mục 2.1 |
| 4. Gán chính thức | Mỗi người một project `MAIN_<tên>` trên Label Studio, gán mù, ảnh các tập trộn lẫn | 5 × 887 lượt, giao diện v1 |
| 5. Đo đồng thuận | Script `src/labeling/19_main_agreement.py` | Mục 3 |
| 6. Phân xử | Claude đề xuất, Khải duyệt | Mục 4 |
| 7. Xem lại pilot | 150 ảnh pilot gán lại theo guide v1: Claude đề xuất, Phúc duyệt | Mục 5 |

### 2.1 Quy tắc chốt (guide v1)

Câu hỏi gốc của mỗi ảnh: *người đi bộ có phải bước xuống lòng đường để đi tiếp dọc vỉa hè gần không?*

1. **Ảnh xem được không?** Ảnh mờ, tối hoặc cháy sáng thì chọn **Không đủ thông tin**.
2. **Có thấy vỉa hè gần không?** Phải có một đoạn mép vỉa hè nằm dưới vạch 3/5 chiều cao ảnh. Gặp lòng đường, vỉa hè ở xa, giao lộ, đầu hẻm hoặc sân rộng thì chọn **Không đủ thông tin**. Xe hoặc người sát camera che quá nửa đoạn vỉa hè cũng chọn **Không đủ thông tin**.
3. **Còn lối đi liên tục không?** Nếu không đi thẳng qua được thì chọn **Bị chặn**.
   - Người đứng, người đi bộ và xe đang chạy không tính là vật cản.
   - Ô tô xét như mọi vật cản khác.
   - Vật cản chỉ tính tới khoảng giữa ảnh.
   - Vỉa hè bị phủ kín cũng là **Bị chặn**.

### 2.2 Phân công

| Tập | Số ảnh | Người gán |
|---|---|---|
| Test | 674 | Học và Loan, cả hai gán mỗi ảnh |
| Val | 486 | Minh và Khải, cả hai gán mỗi ảnh |
| Train | 1.839 | Cả 5 người, mỗi ảnh một người. 276 ảnh (15%) được người thứ hai gán chéo |

Chia tập theo cả tuyến đường, nên không tuyến nào nằm ở hai tập. Chi tiết ở [streets_v1.yaml](../configs/streets_v1.yaml).

## 3. Kết quả gán chính thức

### 3.1 Đồng thuận

| Nhóm ảnh | Cặp gán | Số ảnh | Khớp nhau | κ 3 nhãn | κ chỉ 0/1 |
|---|---|---|---|---|---|
| Test | Học và Loan | 674 | 79% | **0,60** | 0,68 |
| Val | Minh và Khải | 486 | 80% | **0,64** | 0,55 |
| Train gán chéo | 10 cặp | 276 | 78% | **0,61** | 0,56 |

Trên các ảnh gán đôi, các cặp nhãn bất đồng phân bố như sau. Phần lớn là bất đồng về việc ảnh có xét được hay không, ít khi là về chuyện có bị chặn hay không.

| | 0 và I | 1 và I | 0 và 1 |
|---|---|---|---|
| Số ảnh | 193 | 51 | 59 |

### 3.2 Từng người gán

| Người gán | Còn lối đi | Bị chặn | Không đủ thông tin | Giây/ảnh (trung vị) |
|---|---|---|---|---|
| Học | 69% | 10% | 21% | 2,1 |
| Khải | 52% | 8% | 39% | 3,4 |
| Loan | 54% | 6% | 40% | 5,9 |
| Minh | 45% | 5% | 50% | 2,3 |
| Phúc | 47% | 6% | 47% | 7,5 |

Học và Minh có nhiều nhãn bấm dưới 2 giây. Những nhãn này **khớp với người còn lại nhiều hơn** nhãn bấm chậm: test 82% so với 76%, val 89% so với 73%. Vậy bấm nhanh là dấu hiệu ảnh dễ, không phải gán ẩu.

## 4. Phân xử 303 ảnh bất đồng

### 4.1 Cách làm

1. **Claude xem mù.** Claude xem từng ảnh, 12 ảnh một tấm, có kẻ vạch 3/5. Trên ô ảnh không ghi ai gán gì. Mỗi ảnh được ghi một nhãn kèm lý do.
2. **So với phiếu.** 21 ảnh có nhãn đề xuất khác cả hai phiếu. Claude xem lại 21 ảnh này ở cỡ lớn, có hiện phiếu, và sửa 10 ảnh.
3. **Khải duyệt.** Khải xem 11 tấm ảnh ghép, mỗi ô chỉ ghi nhãn đề xuất. Ảnh nào không đồng ý thì Khải ghi nhãn của mình vào cột `phuc` trong [adjudication_proposal.csv](../data/labels/main_report/adjudication_proposal.csv) (tên cột cũ, giữ nguyên để script chạy được; mã nguồn nhãn `adjudicated_phuc` cũng vậy). Nhãn cuối là nhãn của Khải nếu có, còn lại là nhãn đề xuất.

Đề xuất của Claude chỉ là gợi ý cho người phân xử. Mọi nhãn cuối đều đã qua mắt Khải, đúng quy định của đề cương là nhãn do người gán.

### 4.2 Khải sửa gì

Khải sửa **28/303** nhãn đề xuất (9,2%). Cả 28 nhãn sau sửa đều trùng với phiếu của một trong hai người gán ban đầu.

| Thay đổi | Test | Train | Val | Tổng |
|---|---|---|---|---|
| Không đủ thông tin → Còn lối đi | 5 | 1 | 6 | 12 |
| Còn lối đi → Bị chặn | 3 | 2 | 6 | 11 |
| Không đủ thông tin → Bị chặn | 1 | 2 | 1 | 4 |
| Bị chặn → Còn lối đi | 1 | 0 | 0 | 1 |

- Số ô trên tấm ảnh duyệt của 28 ảnh: 0, 42, 64, 65, 76, 81, 97, 98, 109, 112, 116, 122, 141, 145, 162, 168, 169, 196, 215, 221, 234, 269, 272, 275, 283, 286, 294, 300.
- Có 17 ảnh Claude ghi "không chắc", Khải chỉ sửa 1 trong số đó.
- Nhìn chung Khải nới hơn Claude ở câu 2 (vẫn coi là thấy vỉa hè khi vỉa hè ở xa hoặc gần giao lộ), và chặt hơn ở câu 3 (gán "Bị chặn" nhiều hơn).

### 4.3 Kết quả phân xử

| Tập | Còn lối đi | Bị chặn | Không đủ thông tin | Tổng |
|---|---|---|---|---|
| Test | 50 | 16 | 77 | 143 |
| Train | 15 | 8 | 38 | 61 |
| Val | 33 | 19 | 47 | 99 |
| **Tổng** | **98** | **43** | **162** | **303** |

Nhãn cuối trùng với phiếu ban đầu của từng người trên các ảnh bất đồng như sau:

| | Loan | Minh | Phúc | Học | Khải |
|---|---|---|---|---|---|
| Trùng | 92/156 | 79/119 | 27/43 | 61/165 | 37/123 |

Đây là các ảnh khó, được chọn ra chính vì có bất đồng, nên tỉ lệ này **không dùng để chấm điểm người gán**.

## 5. Đưa 150 ảnh pilot vào train

Ảnh pilot thuộc 3 đường train (Pasteur, Lê Văn Sỹ, Phan Đăng Lưu), và không trùng vị trí với bộ chính. Trước đây mỗi ảnh có 5 phiếu, nhưng các phiếu này được gán theo **guide v0**, khi chưa có quy tắc vạch 3/5. Vì vậy cả 150 ảnh được xem lại theo guide v1, không chỉ 35 ảnh bất đồng.

1. **Claude xem mù** cả 150 ảnh, trộn thứ tự, rồi so với phiếu pilot. Có 34 ảnh mà nhãn đề xuất chỉ được 0–1 phiếu ủng hộ. Claude xem lại 34 ảnh này ở cỡ lớn, có hiện phiếu, và sửa 20 ảnh.
2. **Phúc duyệt** 5 tấm ảnh ghép và sửa 3 ảnh ([pilot_adjudication_proposal.csv](../data/labels/pilot_report/pilot_adjudication_proposal.csv), cột `phuc`):
   - ô 6: Bị chặn → Không đủ thông tin (mép vỉa hè nằm trên vạch 3/5);
   - ô 44: Còn lối đi → Bị chặn (bên trái có xe, cây và bàn ghế xếp kín bề ngang);
   - ô 123: Không đủ thông tin → Còn lối đi.

| Mức đồng thuận pilot (v0) | Còn lối đi | Bị chặn | Không đủ thông tin | Tổng |
|---|---|---|---|---|
| Từ 4/5 phiếu trở lên | 63 | 8 | 44 | 115 |
| Từ 3/5 phiếu trở xuống | 10 | 6 | 19 | 35 |
| **Tổng** | **73** | **14** | **63** | **150** |

Có 25 ảnh có nhãn cuối khác nhãn đa số của phiếu v0; 5 ảnh khác hòa phiếu ở v0 nên không có nhãn đa số. Phần lớn là vỉa hè ở xa, giao lộ hoặc đầu hẻm: v0 gán "Còn lối đi" hoặc "Bị chặn", còn v1 xếp vào "Không đủ thông tin".

## 6. Nhãn cuối

File [main_labels_v1.csv](../data/labels/main_labels_v1.csv) có một dòng cho mỗi ảnh, tổng cộng 3.149 dòng. Các cột: `item`, `phase` (main/pilot), `file` (đường dẫn ảnh cắt), `split`, `street_id`, `label` (0/1/I), `source` và `reason`.

| Nguồn nhãn | Số ảnh | Ý nghĩa |
|---|---|---|
| `agreed` | 1.133 | Hai người gán giống nhau |
| `single` | 1.563 | Ảnh train chỉ một người gán |
| `adjudicated_proposal` | 275 | Bất đồng; Khải giữ nguyên nhãn đề xuất |
| `adjudicated_phuc` | 28 | Bất đồng; Khải sửa (tên mã cũ) |
| `pilot_review_proposal` | 147 | Pilot; Phúc giữ nguyên nhãn đề xuất |
| `pilot_review_phuc` | 3 | Pilot; Phúc sửa |

### 6.1 Theo tuyến đường (gồm cả pilot)

| Tập | Đường | Còn lối đi | Bị chặn | Không đủ thông tin |
|---|---|---|---|---|
| Test | Hai Bà Trưng | 121 | 16 | 41 |
| | Lý Thường Kiệt | 195 | 10 | 80 |
| | Nơ Trang Long | 61 | 9 | 24 |
| | Trần Phú | 35 | 12 | 70 |
| Val | Hồng Bàng | 63 | 15 | 72 |
| | Nguyễn Đình Chiểu#0 | 90 | 8 | 134 |
| | Võ Văn Tần | 54 | 12 | 38 |
| Train | Trần Hưng Đạo | 217 | 17 | 114 |
| | Cách Mạng Tháng Tám#0 | 137 | 19 | 67 |
| | Nguyễn Thị Minh Khai | 136 | 8 | 109 |
| | Nguyễn Trãi | 131 | 15 | 144 |
| | Điện Biên Phủ#1 | 106 | 9 | 146 |
| | Phan Đăng Lưu | 100 | 14 | 41 |
| | Lê Văn Sỹ | 100 | 13 | 26 |
| | Nguyễn Kiệm#0 | 38 | 8 | 52 |
| | Hải Thượng Lãn Ông | 24 | 15 | 47 |
| | Pasteur | 23 | 2 | 111 |

### 6.2 Lý do "Không đủ thông tin" (bộ chính)

Lý do chỉ được ghi khi các người gán chọn cùng một lý do. Ảnh pilot không ghi lý do.

| Lý do | Số ảnh |
|---|---|
| Không thấy vỉa hè | 880 |
| Bị che | 139 |
| Ảnh mờ / tối / cháy sáng | 12 |
| Lý do khác | 4 |
| Mỗi người chọn một lý do khác, hoặc có nhãn sau phân xử | 218 |

## 7. Hạn chế và việc còn mở

- **Ít ảnh "Bị chặn".** Tỉ lệ khoảng 10%, trong khi pilot là 19%, vì pilot được lấy mẫu nghiêng về phía ảnh trông như bị chặn. Test chỉ có **47 ảnh dương**, dưới mốc khoảng 60 ảnh của [kế hoạch](data_enrichment.md). Khoảng tin cậy của F1 trên test sẽ rộng. Bơm thêm ảnh cho train đã được hoãn.
- **1.563 ảnh train chỉ có một người gán.** Phần gán chéo 15% có κ 0,61, nên nhãn train có nhiễu nhiều hơn val và test.
- **Khải vừa gán vừa phân xử.** Khải là một trong hai người gán ở 123/303 ảnh bất đồng, gồm cả 99 ảnh bất đồng của val (val do Minh và Khải gán) và 24 ảnh train. Nhãn cuối trùng với phiếu của Khải ở 37 ảnh, trong khi đề xuất mù của Claude trùng ở 32 ảnh; trong 14 nhãn Khải sửa ở các ảnh này, 9 nhãn đổi về phiếu của chính Khải.
- **7 nhãn cuối khác cả hai phiếu** (3 test, 2 val, 2 train): Khải giữ đề xuất của Claude ở các ảnh này.
- **Tỉ lệ "Không đủ thông tin" cao (42%)** do góc chụp từ xe. Riêng Pasteur là 82% (tính cả pilot).
- **Pilot không theo phân phối tự nhiên.** 150 ảnh pilot đã vào train nhưng được lấy mẫu theo tầng điểm của model PoC. EDA và báo cáo cần tách theo `phase`.
- **Label Studio vẫn giữ nguyên phiếu gốc của từng người.** Nhãn cuối nằm trong repo, không ghi ngược lên server.
