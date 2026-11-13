# Gán nhãn

Công cụ: Label Studio Community, tự host (xem [infra/README.md](../infra/README.md)). Mỗi người một project riêng để gán mù. Bản Community không phân quyền, nên quy ước là **chỉ mở project mang tên mình**.

## Quy trình

1. **Pilot** (`PILOT_<tên>`): cả 5 người gán cùng 150 ảnh, độc lập với nhau.
2. **Đo đồng thuận:** chạy `python src/labeling/07_pilot_agreement.py`. Báo cáo nằm ở `data/labels/pilot_report/`.
3. **Họp phân xử:** xem các ảnh bất đồng, chốt quy tắc, cập nhật guide.
4. **Vòng kiểm tra:** gán thêm 50 ảnh theo guide mới. Đạt κ ≥ 0,6 thì sang bước 5.
5. **Gán chính thức** (`MAIN_<tên>`): mỗi người 887 ảnh, trộn lẫn các tập.
6. **Phân xử** các ảnh bất đồng, rồi khóa nhãn và khóa tập test.

**Trạng thái 11/11/2026:** bước 5 và bước 6 đã xong, nhãn cuối (bộ chính và 150 ảnh pilot) ở [main_labels_v1.csv](../data/labels/main_labels_v1.csv), tổng kết ở [labeling_phase1.md](../docs/labeling_phase1.md). Chi tiết bước 5 (5×887 lượt, κ test 0,60, val 0,64, train gán chéo 0,61). Đang ở bước 6: 303 ảnh bất đồng. Claude đã đề xuất nhãn bằng mắt ([adjudication_proposal.csv](../data/labels/main_report/adjudication_proposal.csv)), Phúc duyệt: ảnh nào không đồng ý thì ghi nhãn vào cột `phuc`, rồi chạy lại `19_main_agreement.py` ([báo cáo](../data/labels/main_report/main_report.md), [danh sách](../data/labels/main_report/main_adjudicate.csv)). Tấm ảnh để xem: `python src/labeling/20_review_sheets.py --fetch`, lưu ở `data/labels/main_report/sheets/` (không đưa lên git).

**Đợt 2 (11/11/2026), ảnh bơm cho train:** 2.000 ảnh từ 75 đường mới, mỗi người 400 ảnh, mỗi ảnh một người gán, trong project `MAIN2_<tên>` (giao diện v1, guide v1). Phân công: [train_extra_v1_assignment.csv](../data/manifest/train_extra_v1_assignment.csv). Cách chọn ảnh và kết quả: [docs/data_enrichment.md](../docs/data_enrichment.md) mục 9. **Gán xong 12/11:** 0 = 810, 1 = 588, I = 602 ([báo cáo](../data/labels/train_extra_report/report.md), tính trên nhãn v1). Sau kiểm tra chéo 14/11 (17 nhãn đổi, [train_extra_labels_v2.csv](../data/labels/train_extra_labels_v2.csv)): 0 = 819, 1 = 577, I = 604.

## Phân công gán chính thức

| Tập | Số ảnh | Người gán |
|---|---|---|
| Test | 674 | Học và Loan, gán mù độc lập |
| Val | 486 | Minh và Khải, gán mù độc lập |
| Train | 1.839 | Cả 5 người; 15% được người thứ hai gán chéo |

Chi tiết từng ảnh: [data/manifest/main_v1_assignment.csv](../data/manifest/main_v1_assignment.csv). Phúc gán train và làm người phân xử.

## Tài liệu

| File | Nội dung |
|---|---|
| [guide/bang_tra_nhanh.jpg](guide/bang_tra_nhanh.jpg) | **Bảng tra nhanh:** phím bấm, đặc điểm nhận diện, ảnh ví dụ. Xem cái này khi gán |
| [guide/annotation_guide_v0.md](guide/annotation_guide_v0.md) | Hướng dẫn đang dùng, bảng phím tắt |
| [pilot_review.md](pilot_review.md) | Rà soát pilot, tài liệu cho buổi họp thống nhất |
| [guide/annotation_guide_v1_draft.md](guide/annotation_guide_v1_draft.md) | Dự thảo hướng dẫn v1, đầy đủ, viết lại sau pilot |
| [guide/examples_v1_consensus.jpg](guide/examples_v1_consensus.jpg) | Ảnh ví dụ được nhóm đồng thuận |
| [label_studio/ls_label_config_v0.xml](label_studio/ls_label_config_v0.xml) | Giao diện dùng cho pilot |
| [label_studio/ls_label_config_v1.xml](label_studio/ls_label_config_v1.xml) | Giao diện v1: gộp lý do, chưa đưa lên server |
| [label_studio/annotators.yaml](label_studio/annotators.yaml) | Tên ngắn của người gán |

## Script

| Script | Việc |
|---|---|
| `src/labeling/10_make_pilot_v2.py` | Tạo 150 ảnh pilot (bản ghi, cần model không có trong repo) |
| `src/labeling/06_ls_create_pilot.py` | Tạo project `PILOT_*` |
| `src/labeling/07_pilot_agreement.py` | Kéo nhãn, tính κ, tạo tấm ảnh bất đồng |
| `src/labeling/12_ls_create_main.py` | Phân công và tạo project `MAIN_*` |
| `src/labeling/18_ls_update_main_v1.py` | Chuyển project `MAIN_*` sang giao diện v1, đổi lý do kiểu v0 sang v1 |
| `src/labeling/19_main_agreement.py` | Kéo nhãn bộ chính (chỉ đọc), tính κ theo cặp, lập danh sách phân xử |
| `src/labeling/25_ls_create_train_extra.py` | Tạo project `MAIN2_*` cho 2.000 ảnh bơm của train |
| `src/labeling/26_train_extra_report.py` | Kéo nhãn `MAIN2_*` (chỉ đọc), thống kê theo tầng, đường, người gán; xuất `train_extra_labels_v1.csv` |
| `src/labeling/20_review_sheets.py` | Tấm ảnh các ca bất đồng, hoặc tấm ảnh nhãn đề xuất để đối chiếu bằng mắt |
