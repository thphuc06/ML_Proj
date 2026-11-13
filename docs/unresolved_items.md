# Danh sách việc chưa giải quyết

Cập nhật 11/11/2026: đợt gán nhãn 1 đã xong, đã có nhãn cuối ([tổng kết](labeling_phase1.md)). **Bơm thêm ảnh tạm hoãn** theo quyết định của Phúc ([báo cáo](../data/labels/main_report/main_report.md)). Mỗi mục đóng lại khi có bằng chứng tương ứng.

## Đã đóng nhờ đợt gán chính

| # | Vấn đề | Bằng chứng |
|---|---|---|
| 1 | Fleiss κ pilot 0,57, chưa đạt 0,6 | Trên bộ chính, κ 3 nhãn: test 0,60 (Học–Loan), val 0,64 (Minh–Khải), train gán chéo 0,61 |
| 4 | Tỉ lệ "Bị chặn" của mỗi người lệch nhau từ 8% đến 25% | Trên bộ chính, các tỉ lệ này còn 5–10%. Các ảnh không giống nhau nên số này chỉ để tham khảo |
| 5 | Label Studio chưa có giao diện v1 | Cả 5 project `MAIN_*` đã dùng giao diện v1 và không còn lý do kiểu v0 (`18_ls_update_main_v1.py`) |
| 2, 15 | Guide v1 còn là dự thảo; ngưỡng "lối hẹp" chưa chốt | Phúc xác nhận ngày 11/11: chốt guide v1 nguyên văn, kể cả các đề xuất "(chờ họp)". Lối hẹp: không đi thẳng qua được thì là bị chặn. Không thêm ô phụ |
| 19 | 303 ảnh có hai phiếu khác nhau | Đã phân xử: Claude đề xuất bằng mắt, Phúc duyệt và sửa 28 ảnh ([chi tiết](labeling_phase1.md#4-phân-xử-303-ảnh-bất-đồng)) |
| 3 | Ảnh pilot chưa có nhãn cuối | Cả 150 ảnh đã được xem lại theo guide v1 (Phúc sửa 3 ảnh) và đưa vào train với `phase=pilot` ([chi tiết](labeling_phase1.md#5-đưa-150-ảnh-pilot-vào-train)) |
| 12 | Chưa có bảng nhãn cuối | [main_labels_v1.csv](../data/labels/main_labels_v1.csv): một dòng cho mỗi ảnh, có cột nguồn nhãn |
| 6 | Chưa biết bộ chính dùng được bao nhiêu ảnh | 1.746 ảnh dùng được (0 hoặc 1), 1.253 ảnh "Không đủ thông tin" (42%) |

## Việc tiếp theo (bơm ảnh đã gán xong)

| # | Vấn đề | Việc cần làm |
|---|---|---|
| 7 | **Ảnh "Bị chặn" ít hơn ước tính nhiều.** Nhãn cuối: train 120/1.132 ảnh dùng được (gồm pilot), val 35/242, test **47/459**. Tỉ lệ khoảng 10%, trong khi pilot là 19% | **Test dưới mốc khoảng 60 ảnh dương.** Nhóm cần quyết định có đổi hoặc thêm đường test **trước khi** train model |
| 18 | Bộ chấm `occ_v2` chưa được kiểm chứng | **Đã đóng (11/11).** `21_selector_benchmark.py` đo trên 1.839 ảnh main của train (106 ảnh dương), giữ nguyên một đường ra ngoài: `occ_v2` không hơn `occ_v1` (hiệu tỉ lệ trúng top 20% của v1 so với v2: +0,014 [−0,014; +0,041]), và cả hai thua logistic trên embedding DINOv2 (0,220 so với 0,139; hiệu +0,082 [+0,043; +0,117]). Bộ mới thay `occ_v2`; script 17 không cần chạy nữa ([mục 7](data_enrichment.md)). Còn lại: chưa có nhãn người trên đường mới để kiểm chứng tỉ lệ trúng |
| 17 | Train thiếu ảnh dương: 120 ảnh (gồm 14 ảnh pilot) so với mức ước tính 200–245 | **Đã gán xong (12/11), kiểm tra chéo một phần (14/11).** 2.000 ảnh: 577 "Bị chặn" (588 trước kiểm tra chéo); train từ 120 lên 697 ảnh dương trên 2.528 ảnh dùng được. Tầng theo điểm 0,386, tầng ngẫu nhiên 0,078; gấp 1,8 lần bốc ngẫu nhiên từ cùng kho ([kết quả](data_enrichment.md#kết-quả-gán-12112026)). **Còn lại:** (1) người gán chênh nhau rõ trên cùng loại ảnh (Học 43% "Bị chặn", Loan 19%; χ² p = 4·10⁻¹⁵), mỗi ảnh một người nên chưa biết ai đúng. Claude xem lại thử (13/11) nhưng Phúc bỏ vì phần lớn đề xuất sai. Một người trong nhóm kiểm tra chéo 203 trong 264 ảnh Claude nghi ngờ (14/11): trùng nhãn gốc 186/203, **17 nhãn đổi** (`train_extra_labels_v2.csv`). 61 ảnh trong danh sách chưa có nhãn kiểm tra, và 2 ô cuối của danh sách (263, 264) ghi chưa rõ nên giữ nhãn gốc, chờ người kiểm tra xác nhận; (2) gộp `train_extra_labels_v2.csv` vào bộ train; (3) 83% ảnh dương của train là ảnh chọn theo điểm, phần lớn từ đường nhỏ |
| 20 | Ảnh "Bị chặn" không gắn vật cản: Phúc 10/52, Loan 6/53, Khải 3/74 | Chỉ ảnh hưởng thông tin phụ, không ảnh hưởng nhãn. Ghi trong EDA nếu phân tích theo loại vật cản |
| 22 | 1.563 ảnh train chỉ có một người gán | Có thể rà riêng 88 ảnh "Bị chặn" chỉ một người gán (lớp hiếm, sai một ảnh ảnh hưởng nhiều) |

## Cần xác nhận với nhóm

| # | Vấn đề | Ghi chú |
|---|---|---|
| 16 | Vòng kiểm tra 50 ảnh | Repo chưa ghi lại vòng này. Nếu đã bỏ qua thì ghi lý do. κ của bộ chính đã thay vai trò kiểm tra |

## Theo dõi

| # | Vấn đề | Việc cần làm |
|---|---|---|
| 8 | Vỉa hè bên trái của đường một chiều ít được quan sát | Ghi vào phần giới hạn của báo cáo; ảnh nhóm tự chụp có thể bù một phần |
| 21 | Tỉ lệ "Không đủ thông tin" cao: 36% số ảnh, Pasteur 81%, Hải Thượng Lãn Ông 57%, Điện Biên Phủ 54% | Ghi vào EDA. Khi chọn đường train mới, ưu tiên đường thấy rõ vỉa hè phải |

## Còn thiếu theo Step 2–3 của đề cương

| # | Vấn đề | Việc cần làm |
|---|---|---|
| 9 | Chưa dò ảnh gần trùng bằng nội dung ảnh | Thêm bước dò gần trùng trước khi khóa split |
| 10 | Chưa rà soát nội dung nhạy cảm trong ảnh | Rà soát theo Step 3 |
| 11 | Ảnh bị bộ lọc đêm loại chưa được kiểm tra ngẫu nhiên | Xem lại 58 ảnh bị loại |
| 13 | Chưa có ít nhất 100 ảnh nhóm tự chụp | Lên kế hoạch chụp, ghi mã buổi chụp |
| 14 | Chưa có EDA và danh sách split đã khóa | Làm tiếp. Nhãn cuối đã có, còn chờ quyết định về đường test |
