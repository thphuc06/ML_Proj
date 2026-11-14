# Báo cáo về dữ liệu

Báo cáo theo khung `ml-data.pdf` của môn học. Bản PDF: [data_report.pdf](data_report.pdf).

| Thư mục / file | Nội dung |
|---|---|
| `main.tex`, `sections/`, `references.bib` | Mã LaTeX. Dùng lại `fit_hcmus.sty` và logo ở `../proposal/latex/` |
| `figures/` | Hình của báo cáo (`tab_*`, `img_*`, `dup_*`). Các tấm ảnh kiểm tra `*_sheet_*.jpg` có ảnh val/test nên không vào git |
| `tables/` | Bảng số liệu EDA (CSV) và ba file `*_numbers.json` chứa các số chính |
| `make.sh` | Biên dịch bằng XeLaTeX: `sh make.sh` (Git Bash), ra `data_report.pdf` |

Số liệu và hình sinh từ các script trong [`src/eda/`](../../src/eda/), chạy từ thư mục gốc của repo:

```bash
python src/eda/27_rebuild_missing_crops.py   # dựng lại ảnh cắt còn thiếu, cần MAPILLARY_TOKEN
python src/eda/28_eda_tabular.py             # metadata và nhãn
python src/eda/29_eda_images.py              # thống kê điểm ảnh
python src/eda/30_eda_duplicates.py          # trùng lặp, rò rỉ giữa các tập, đa dạng (nên chạy trên GPU)
```

Nhãn val/test chỉ dùng để thống kê mô tả. Ảnh: © Mapillary contributors, CC BY-SA 4.0.

## Chạy lại EDA

Tạo virtualenv và chạy `python -m pip install -r requirements.txt`. Ghi lại phiên bản Python và `pip freeze` của môi trường thực sự sinh kết quả; môi trường hiện tại chưa chạy lại toàn bộ EDA.

Ảnh không có trong Git. Lấy bản ảnh từ server vào `data/crops/`, hoặc cấu hình MAPILLARY_TOKEN rồi chạy script 27 để dựng lại. Ghi rõ nguồn ảnh vì nén JPEG có thể làm thay đổi phép đo. Chạy lần lượt 28, 29, 30; script 28 chỉ cần bảng dữ liệu, script 30 cần model và nên dùng GPU.

Trước khi train, chốt cách xử lý ảnh gần giao lộ, lưu manifest có phiên bản và chạy lại thống kê. Không đổi đường test dựa trên số nhãn dương đã xem.

## Hai bản báo cáo

- Tiếng Việt: `sh make.sh`, xuất `data_report.pdf`.
- Tiếng Anh: `sh make.sh en`, xuất `data_report_en.pdf`; nguồn `main_en.tex` và `sections_en/report.tex`.

Bản tiếng Anh giữ số liệu, kết quả và hạn chế của bản tiếng Việt. Biểu đồ vector có bản dịch nhãn trong `figures_en/` (số theo kiểu tiếng Anh, 1,839), giữ nguyên dữ liệu và hình học của biểu đồ. Bản tiếng Việt dùng `figures_vi/`: cùng biểu đồ gốc, chỉ thay tên nhóm kiểu mã (`train_extra`, `top_score`, `main`) bằng tên dùng trong báo cáo (ảnh bổ sung, tầng điểm cao, bộ chính; "dùng được" thành "hợp lệ"). Ảnh ghép ví dụ giữ nguyên chú thích raster. Để tạo lại hai bộ hình này, cài PyMuPDF (`python -m pip install pymupdf`) rồi chạy `python docs/data_report/translate_figures.py` từ gốc repo trước khi build (script dùng font Arial của Windows).

Báo cáo không nhắc tới tên file, script hay tên biến, trừ bảng tổ chức thư mục ở mục 5; nguồn của từng số liệu được mô tả ở phụ lục A.

Mã `adjudicated_phuc` là mã cũ trong CSV, được giữ để tương thích; theo xác nhận của nhóm, Khải thực hiện phân xử 303 ảnh bộ chính. Không đổi nhãn hay số đếm khi sửa thông tin này.
