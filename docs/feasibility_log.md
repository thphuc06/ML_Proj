# Nhật ký khả thi (Week 3)

Trả lời các câu hỏi mà pilot phải xác nhận theo mục 2.3 và Step 1–2 của đề cương. Số liệu lấy từ dữ liệu thu thập và 150 ảnh pilot; chi tiết ở [collection_log.md](collection_log.md). Cập nhật 01/11/2026.

| Câu hỏi | Kết quả | Kết luận |
|---|---|---|
| Truy cập được nguồn ảnh không? | Mapillary API hoạt động: 652.159 ảnh 360° trong khu vực nghiên cứu, 1.234 chuỗi ảnh. Chỉ 2 ô rất nhỏ bị lỗi khi quét. | Đạt |
| Có đủ tọa độ và thời gian chụp không? | Có tọa độ và ngày chụp. **Giờ chụp không đáng tin:** ảnh ghi 18–0 giờ vẫn sáng như ban ngày. | Đạt, không lọc theo giờ |
| Điều kiện sử dụng? | Ảnh theo giấy phép CC BY-SA 4.0, cần ghi công Mapillary contributors. Phần làm mờ mặt người và biển số được giữ nguyên. | Đạt |
| Có đủ ảnh theo tuyến đường không? | 17 tuyến, 2.999 ảnh chính và 150 ảnh pilot. 58 ảnh đêm bị loại theo độ sáng. | Đạt |
| Ảnh có thấy vỉa hè không? | Ảnh trái thấy vỉa hè gần ở khoảng 7% số ảnh, ảnh phải khoảng 38% (đo tự động, khắt khe). Nên chỉ dùng ảnh phải. | Đạt với ảnh phải |
| Tỉ lệ ảnh dùng được? | Pilot: 44/150 ảnh (29%) được đa số chọn "Không đủ thông tin". Riêng đường Pasteur 54%. | Đạt; bộ chính cần đo lại |
| Thời gian gán nhãn? | Trung vị 4,7–12,6 giây/ảnh tùy người. | Đạt |
| Đồng thuận giữa người gán? | Fleiss κ 3 lựa chọn 0,57; đủ thông tin hay không 0,65; còn lối đi hay bị chặn 0,49. | **Chưa đạt ngưỡng 0,6** |
| Cân bằng lớp? | 19 trong 101 ảnh có đa số chọn 0 hoặc 1 là "bị chặn" (19%). | Lệch lớp, cần theo dõi |
| Hạ tầng gán nhãn? | Label Studio tự host trên AWS, khoảng 1,35 USD/ngày khi bật. Đã thử tắt/bật lại: dữ liệu giữ nguyên. | Đạt |

## Kết luận

Hướng dữ liệu khả thi: nguồn ảnh, metadata, giấy phép, số lượng và thời gian gán đều đạt. Rủi ro còn lại là **độ đồng thuận về ranh giới "bị chặn"** và **lệch lớp**. Hai rủi ro này được theo dõi trong [unresolved_items.md](unresolved_items.md).

Ước tính khoảng 55% ảnh bộ chính thấy rõ vỉa hè chỉ dựa trên 40 ảnh ngẫu nhiên xem bằng mắt, chưa phải nhãn người, nên số ảnh dùng được thực tế sẽ biết sau khi gán.
