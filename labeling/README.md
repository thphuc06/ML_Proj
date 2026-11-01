# Gán nhãn

Công cụ: Label Studio Community, tự host (xem [infra/README.md](../infra/README.md)). Mỗi người một project riêng để gán mù. Bản Community không phân quyền, nên quy ước là **chỉ mở project mang tên mình**.

## Quy trình

1. **Pilot** (`PILOT_<tên>`): cả 5 người gán cùng 150 ảnh, độc lập với nhau.
2. **Đo đồng thuận:** chạy `python src/labeling/07_pilot_agreement.py`. Báo cáo nằm ở `data/labels/pilot_report/`.
3. **Họp phân xử:** xem các ảnh bất đồng, chốt quy tắc, cập nhật guide.
4. **Vòng kiểm tra:** gán thêm 50 ảnh theo guide mới. Đạt κ ≥ 0,6 thì sang bước 5.
5. **Gán chính thức** (`MAIN_<tên>`): mỗi người 887 ảnh, trộn lẫn các tập.
6. **Phân xử** các ảnh bất đồng, rồi khóa nhãn và khóa tập test.

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
| [guide/annotation_guide_v0.md](guide/annotation_guide_v0.md) | Hướng dẫn đang dùng, bảng phím tắt |
| [pilot_review.md](pilot_review.md) | Rà soát pilot, tài liệu cho buổi họp thống nhất |
| [guide/annotation_guide_v1_draft.md](guide/annotation_guide_v1_draft.md) | Dự thảo v1, quy tắc R1–R9 rút ra từ pilot |
| [guide/examples_v1_consensus.jpg](guide/examples_v1_consensus.jpg) | Ảnh ví dụ được nhóm đồng thuận |
| [label_studio/ls_label_config_v0.xml](label_studio/ls_label_config_v0.xml) | Giao diện gán nhãn |
| [label_studio/annotators.yaml](label_studio/annotators.yaml) | Tên ngắn của người gán |

## Script

| Script | Việc |
|---|---|
| `src/labeling/10_make_pilot_v2.py` | Tạo 150 ảnh pilot (bản ghi, cần model không có trong repo) |
| `src/labeling/06_ls_create_pilot.py` | Tạo project `PILOT_*` |
| `src/labeling/07_pilot_agreement.py` | Kéo nhãn, tính κ, tạo tấm ảnh bất đồng |
| `src/labeling/12_ls_create_main.py` | Phân công và tạo project `MAIN_*` |
