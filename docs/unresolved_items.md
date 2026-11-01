# Danh sách việc chưa giải quyết (Week 3)

Cập nhật 01/11/2026. Mỗi mục đóng lại khi có bằng chứng tương ứng.

## Chặn việc gán nhãn chính thức

| # | Vấn đề | Việc cần làm |
|---|---|---|
| 1 | Fleiss κ pilot 0,57, chưa đạt ngưỡng 0,6 | Chốt guide v1, gán vòng kiểm tra 50 ảnh, đạt thì mở `MAIN` |
| 2 | Các quy tắc trong guide v1 mới là dự thảo ([xem](../labeling/guide/annotation_guide_v1_draft.md)) | Nhóm họp, chốt từng quy tắc và chọn ảnh mẫu |
| 3 | 35 ảnh pilot có từ 3/5 phiếu trở xuống chưa có nhãn cuối ([danh sách](../data/labels/pilot_report/pilot_disagreements_20261029_0903.csv)) | Phân xử trong buổi họp, ghi lý do |
| 4 | Mỗi người có ngưỡng "bị chặn" khác nhau: từ 8% (Loan) đến 25% (Minh) | Thống nhất bằng ảnh mẫu, kiểm tra lại ở vòng 50 ảnh |
| 5 | Label Studio chưa cập nhật giao diện v1: gộp lý do "Không thấy vỉa hè", bắt buộc chọn vật cản khi "Bị chặn" | Cập nhật sau khi chốt guide v1 |

## Theo dõi trong lúc gán nhãn

| # | Vấn đề | Việc cần làm |
|---|---|---|
| 6 | Số ảnh dùng được của bộ chính chưa biết, ước tính khoảng 1.700 | Đo trong lúc gán; thiếu thì thêm đường dự phòng |
| 7 | Lớp "bị chặn" chiếm khoảng 19% | Sau khi gán, kiểm tra tập test có đủ cả hai lớp trước khi khóa |
| 8 | Vỉa hè bên trái của đường một chiều ít được quan sát | Ghi vào phần giới hạn của báo cáo; ảnh nhóm tự chụp có thể bù một phần |

## Còn thiếu theo Step 2–3 của đề cương

| # | Vấn đề | Việc cần làm |
|---|---|---|
| 9 | Mới loại ảnh trùng tuyệt đối và gom ảnh cùng vị trí, chưa dò ảnh gần trùng bằng nội dung ảnh | Thêm bước dò gần trùng trước khi khóa split |
| 10 | Chưa rà soát nội dung nhạy cảm trong ảnh | Rà soát theo Step 3 |
| 11 | Ảnh bị bộ lọc đêm loại chưa được kiểm tra ngẫu nhiên | Xem lại 58 ảnh bị loại |
| 12 | Danh sách ảnh chưa có cột người gán và trạng thái rà soát | Thêm khi chốt nhãn; hiện người gán nằm trong `main_v1_assignment.csv` |
| 13 | Chưa có ít nhất 100 ảnh nhóm tự chụp | Lên kế hoạch chụp, ghi mã buổi chụp |
| 14 | Chưa có EDA và danh sách split đã khóa | Làm sau khi gán xong |
