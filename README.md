# Phân loại tình trạng chặn lối đi trên vỉa hè TP.HCM từ ảnh đường phố

Đồ án môn Nhập môn Học máy (CSC14005), Nhóm 11, lớp 24KHMT02, FIT HCMUS.

Bài toán là phân loại nhị phân: với một ảnh chụp một phía vỉa hè, người đi bộ **còn lối đi** (0) hay **bị chặn** (1). Ảnh không đủ bằng chứng được ghi nhận riêng và loại khỏi model. Câu hỏi chính: model nào phân loại tốt nhất trên **các tuyến đường không có trong tập train**.

Đề cương đầy đủ: [docs/proposal/11-project-proposal.pdf](docs/proposal/11-project-proposal.pdf).

## Tiến độ theo mốc của đề cương

Cập nhật 11/11/2026: **đợt gán nhãn 1 đã xong.** Đã có nhãn cuối cho 2.999 ảnh, trong đó 1.746 ảnh dùng được (188 ảnh "Bị chặn"). Tổng kết ở [docs/labeling_phase1.md](docs/labeling_phase1.md). Chưa bơm thêm ảnh, chưa làm EDA.

**Week 3**

| Bằng chứng | Trạng thái |
|---|---|
| Đề cương | Xong ([PDF](docs/proposal/11-project-proposal.pdf)) |
| Guide gán nhãn | [v0](labeling/guide/annotation_guide_v0.md) dùng cho pilot; [v1](labeling/guide/annotation_guide_v1_draft.md) dùng cho bộ chính, đã chốt nguyên văn, kể cả các đề xuất "(chờ họp)" |
| Nhật ký pilot và khả thi | Xong ([báo cáo pilot](data/labels/pilot_report/pilot_report_20261029_0903.md), [khả thi](docs/feasibility_log.md), [nhật ký dữ liệu](docs/collection_log.md)) |
| Khung giao diện | Đã có ([app/](app/)): quan sát mẫu với metadata thật, chưa có model |
| Danh sách việc chưa giải quyết | Có ([unresolved_items.md](docs/unresolved_items.md)) |
| Tổng kết gán nhãn đợt 1 | Có ([labeling_phase1.md](docs/labeling_phase1.md)) |

**By Week 6**

| Việc | Trạng thái |
|---|---|
| Thu thập ảnh | Xong phần Mapillary: 2.999 ảnh chính, 150 ảnh pilot ([danh sách ảnh](data/manifest/main_v1.csv)). Chưa có ảnh nhóm tự chụp |
| Gán nhãn | **Đợt 1 xong.** Bộ chính: 5×887 lượt, κ test 0,60, val 0,64, train gán chéo 0,61. 303 ảnh bất đồng đã phân xử, Phúc sửa 28 ảnh. Nhãn cuối ở [main_labels_v1.csv](data/labels/main_labels_v1.csv): train 106/1.045, val 35/242, test 47/459 (Bị chặn / dùng được). Còn 35 ảnh pilot chưa có nhãn cuối |
| Tiền xử lý | Một phần: đã cắt ảnh, lọc ảnh đêm, loại trùng tuyệt đối. Còn dò gần trùng và rà soát nội dung nhạy cảm |
| EDA | Chưa làm |
| Chia tập | Đã chia theo đường ([streets_v1.yaml](configs/streets_v1.yaml)), chưa khóa |
| Bơm thêm ảnh "Bị chặn" cho train | Tạm hoãn, làm sau. Số ảnh "Bị chặn" thực tế: train 106, val 35, test 47, ít hơn ước tính ([ghi chép](docs/data_enrichment.md)) |

## Cấu trúc thư mục

```text
.
├── configs/            Danh sách đường và cách chia tập
├── labeling/           Mọi thứ cho việc gán nhãn
│   ├── guide/          Hướng dẫn gán nhãn, ảnh ví dụ
│   └── label_studio/   Giao diện gán nhãn, danh sách người gán
├── src/
│   ├── common.py       Đường dẫn, quy tắc cắt ảnh, hàm địa lý
│   ├── seg_measures.py Đo vỉa hè và xe đậu bằng SegFormer, chỉ để chọn mẫu
│   ├── ls_client.py    Kết nối Label Studio
│   ├── collection/     OSM, metadata Mapillary, xếp hạng đường, thu thập ảnh
│   ├── labeling/       Tạo pilot và project, tính đồng thuận
│   └── analysis/       Các phân tích thăm dò dẫn tới quyết định dữ liệu
├── data/
│   ├── manifest/       Nguồn gốc từng ảnh, phân công gán nhãn
│   ├── streets/        Bảng xếp hạng và phân tích đường
│   └── labels/         Báo cáo và nhãn pilot
├── docs/
│   ├── proposal/       Đề cương (PDF và mã LaTeX)
│   ├── figures/        Ảnh minh họa cho tài liệu
│   ├── collection_log.md
│   ├── data_enrichment.md
│   ├── labeling_phase1.md
│   ├── feasibility_log.md
│   └── unresolved_items.md
├── app/                Khung web/API (chưa có model)
└── infra/              Dựng server Label Studio trên AWS
```

Không có trong repo (xem [.gitignore](.gitignore)): ảnh gốc và ảnh cắt, token và mật khẩu.

## Cài đặt

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
cp .env.example .env                               # điền MAPILLARY_TOKEN
cp infra/.env.server.example infra/.env.server     # chỉ cần khi làm việc với Label Studio
```

## Chạy pipeline

Chạy từ thư mục gốc của repo. Các script được đánh số theo thứ tự thực hiện.

```bash
python src/collection/01_osm_streets.py            # đường và điểm ngữ cảnh từ OSM
python src/collection/02_fetch_mapillary_meta.py   # metadata ảnh 360°
python src/collection/03_rank_streets.py           # gắn ảnh vào đường, xếp hạng đường
python src/collection/11_collect_main.py --dry     # đếm số ảnh, bỏ --dry để tải và cắt thật

python src/labeling/07_pilot_agreement.py          # tính đồng thuận pilot
python src/labeling/19_main_agreement.py --fresh   # kéo nhãn bộ chính (chỉ đọc), tính κ, lập danh sách phân xử, xuất nhãn cuối
python src/labeling/20_review_sheets.py --fetch    # tấm ảnh các ca bất đồng; --proposal file.csv để xem nhãn đề xuất
```

`04_street_preview.py` và `10_make_pilot_v2.py` được giữ làm bản ghi cách chọn đường và lấy mẫu pilot. Bước chấm điểm của hai script này cần một model từ đợt thử trước, model đó không có trong repo nên hai script không chạy nguyên trạng. Kết quả đã chốt trong `configs/streets_v1.yaml`, `data/streets/` và `data/manifest/pilot_v2.csv`.

Thử nghiệm bơm thêm ảnh "Bị chặn" cho train (không bắt buộc, xem [docs/data_enrichment.md](docs/data_enrichment.md)):

```bash
python src/analysis/16_train_extra_preview.py --sample 80   # tập nhỏ, có --dry để chỉ đếm
python src/analysis/17_check_scorer_pilot.py                # so bộ chấm điểm trên phiếu pilot, nên chạy trên GPU
```

Chạy khung giao diện:

```bash
python -m uvicorn app.main:app --port 8000     # mở http://127.0.0.1:8000
```

## Quy tắc dữ liệu chính

- Nguồn: ảnh 360° trên Mapillary (2023–2024), giấy phép CC BY-SA 4.0, © Mapillary contributors.
- Cắt ảnh: chỉ lấy bên phải xe, nhìn chếch 60° so với hướng đi, chúc xuống 4°, khung 90°, 640×640.
- Lọc: chỉ theo quy tắc (ảnh đêm theo độ sáng, ảnh trùng). Không lọc bằng model. Giờ chụp trên Mapillary không đáng tin nên không dùng để lọc.
- Chia tập theo cả tuyến đường, nên không tuyến nào nằm ở hai tập.
- Điểm của model (PoC, SegFormer) chỉ được dùng để chọn mẫu, có ghi tầng vào manifest, không bao giờ dùng làm nhãn. Mọi ảnh bơm thêm chỉ vào train. Val và test giữ phân phối tự nhiên.
