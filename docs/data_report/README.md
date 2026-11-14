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
