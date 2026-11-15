# Báo cáo về dữ liệu

Báo cáo theo khung `ml-data.pdf` của môn học. Bản chính là bản tiếng Anh: [data_report_en.pdf](data_report_en.pdf). Bản tiếng Việt là bản dịch, được cập nhật song song: [data_report.pdf](data_report.pdf).

| Thư mục / file | Nội dung |
|---|---|
| `main_en.tex`, `sections_en/report.tex` | Mã LaTeX của bản tiếng Anh (bản chính) |
| `main.tex`, `sections/`, `references.bib` | Mã LaTeX của bản tiếng Việt và danh mục tài liệu tham khảo dùng chung. Cả hai bản dùng lại `fit_hcmus.sty` và logo ở `../proposal/latex/` |
| `figures/` | Hình của báo cáo (`tab_*`, `img_*`, `dup_*`). Các tấm ảnh kiểm tra `*_sheet_*.jpg` có ảnh val/test nên không vào git |
| `tables/` | Bảng số liệu EDA (CSV) và ba file `*_numbers.json` chứa các số chính |
| `make.sh` | Biên dịch bằng XeLaTeX (Git Bash): `sh make.sh en` ra `data_report_en.pdf`, `sh make.sh` ra `data_report.pdf` |

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

- Tiếng Anh (bản chính): `sh make.sh en`, xuất `data_report_en.pdf`; nguồn `main_en.tex` và `sections_en/report.tex`.
- Tiếng Việt (bản dịch): `sh make.sh`, xuất `data_report.pdf`; nguồn `main.tex` và `sections/`.

Khi sửa nội dung, sửa bản tiếng Anh trước rồi đồng bộ sang bản tiếng Việt và build lại cả hai PDF. Hai bản phải có cùng số liệu, kết quả và hạn chế. Biểu đồ vector có bản dịch nhãn trong `figures_en/` (số theo kiểu tiếng Anh, 1,839), giữ nguyên dữ liệu và hình học của biểu đồ. Bản tiếng Việt dùng `figures_vi/`: cùng biểu đồ gốc, chỉ thay tên nhóm kiểu mã (`train_extra`, `top_score`, `main`) bằng tên dùng trong báo cáo (ảnh bổ sung, tầng điểm cao, bộ chính; "dùng được" thành "hợp lệ"). Ảnh ghép ví dụ giữ nguyên chú thích raster. Để tạo lại hai bộ hình này, cài PyMuPDF (`python -m pip install pymupdf`) rồi chạy `python docs/data_report/translate_figures.py` từ gốc repo trước khi build (script dùng font Arial của Windows).

Báo cáo không nhắc tới tên file, script hay tên biến, trừ bảng tổ chức thư mục ở mục 5; nguồn của từng số liệu được mô tả ở phụ lục A.

## Quy ước câu chữ (cập nhật 15/11/2026)

- Mỗi khái niệm một tên. Tiếng Anh: *main component*, *enrichment set*, *train-side*, *usable* (nhãn 0/1), *legible* (ảnh đủ rõ để đánh giá). Tiếng Việt: bộ chính, ảnh bổ sung, phía train, ảnh hợp lệ, ảnh quan sát được.
- "Visual review" / "kiểm tra trực quan" là quan sát của trợ lý AI Claude trên bảng ảnh tổng hợp, không phải nhãn của người và không phải phép đo. Phải nói rõ điều này ngay ở phần thuật ngữ.
- Độ sáng có hai đại lượng: của ảnh 360° (*panorama brightness*, dùng để lọc ảnh đêm) và của ảnh cắt (*crop luminance*). Luôn ghi rõ là đại lượng nào.
- Thuật ngữ tiếng Việt: giá trị ngoại lai (outlier), bách phân vị (percentile), kiểm định chéo (cross-validation), tỉ lệ thu được mẫu dương (yield).
- Khác biệt giữa ảnh bổ sung và bộ chính được giải thích bằng loại đường (71% ảnh bổ sung từ đường tertiary hoặc residential; cả 17 đường bộ chính là primary hoặc secondary). Không viết "đường gần chợ": 38/75 đường bổ sung có chợ trong 150 m, nhưng bộ chính là 12/17, nên chợ không phân biệt hai phần.
- Kết luận dựa trên quan sát trực quan hoặc suy luận viết ở mức "có vẻ", "nhiều khả năng"; chỉ khẳng định điều đã đo.

Khải thực hiện phân xử 303 ảnh bất đồng của bộ chính. Ngày 15/11/2026, cột `phuc` của bảng đề xuất phân xử bộ chính được đổi tên thành `khai` và mã nguồn nhãn `adjudicated_phuc` thành `adjudicated_khai` cho khớp; không nhãn hay số đếm nào thay đổi. Cột `phuc` và mã `pilot_review_phuc` của phần pilot giữ nguyên vì Phúc là người duyệt 150 ảnh pilot.
