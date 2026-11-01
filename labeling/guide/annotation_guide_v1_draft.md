# Guide v1 – DỰ THẢO (chốt tại buổi họp pilot)

Các quy tắc dưới đây rút ra từ 35 ảnh bất đồng của pilot (`data/labels/pilot_report/pilot_disagreements_*.jpg`). Mã `#n` là số thứ tự ảnh trong tấm ghép bất đồng. Mọi quy tắc của v0 vẫn giữ nguyên, trừ chỗ được sửa dưới đây.

## Quy tắc mới / sửa

**R1 – Đoạn được đánh giá** (lỗi lớn nhất của v0)
- Chỉ xét đoạn vỉa hè gần, từ **mép dưới ảnh ra tới khoảng 20 m phía trước**. Mốc: tới khoảng **giữa ảnh theo chiều sâu**, hoặc tới **giao lộ gần nhất**, lấy mốc nào gần hơn.
- Vật cản ở xa hơn mốc đó thì **không tính**. Ở khoảng cách ấy người và xe trông chỉ nhỏ bằng đốt ngón tay.

**R2 – Thế nào là "thấy vỉa hè gần"**
- Phải thấy **mặt vỉa hè** (gạch hoặc bê tông sát mép đường) trải trên **ít nhất khoảng 1/3 bề ngang** nửa dưới ảnh.
- Chỉ thấy lòng đường, dải phân cách, hoặc vỉa hè nằm xa phía sau thì chọn **D → F**.
- Ảnh liên quan: #5, #9, #18, #19, #20, #27, #28, #30.

**R3 – Giao lộ**
- Nếu đoạn vỉa hè thấy được chủ yếu là **góc giao lộ hoặc vạch qua đường**, không có đoạn vỉa hè chạy dọc, thì chọn **D → lý do mới "Giao lộ / góc đường"**.
- Ảnh liên quan: #1, #8, #21, #24, #34.

**R4 – Bị che ở tiền cảnh**
- Xe hoặc người **đang di chuyển** ngay sát camera che **quá nửa** đoạn ở R1 thì chọn **D → H**.
- Nếu che ít hơn, chấm theo phần còn lại.
- Ảnh liên quan: #2, #3, #4, #6, #7, #10, #14, #15.

**R5 – Ngưỡng "Bị chặn"** (bất đồng 0 vs 1)
- Lấy **bề ngang một chiếc xe máy (khoảng 0,7 m)** làm thước đo.
- Ở ít nhất một chỗ trong đoạn R1, dải trống **hẹp hơn một xe máy** thì là **1 – Bị chặn**: người đi phải xuống lòng đường hoặc lách giữa xe và đồ vật.
- Xe máy đậu thành hàng nhưng vẫn chừa dải trống **≥ một xe máy** liên tục thì là **0**.
- Bàn ghế, quầy hàng hay hàng hóa chiếm hết bề ngang ở một chỗ thì là **1**, dù phần còn lại trống.
- Ảnh liên quan: #0, #11, #12, #16, #17, #22, #23, #25, #26, #29, #31, #32.

**R6 – Vỉa hè phủ kín vẫn là 1, không phải D**
- Đông xe hoặc đông hàng tới mức không thấy mặt vỉa hè, nhưng rõ ràng vỉa hè nằm dưới đó, thì chọn **1**.
- Ảnh liên quan: #21, #34. Hai ảnh này đang bị chia giữa 1 và D.

## Thay đổi giao diện (đề xuất)

- Khi chọn **S (Bị chặn)**: **bắt buộc chọn ít nhất 1 vật cản** (Q–Y), để có nguyên nhân chặn cho mọi ảnh bị chặn.
- Thêm lý do **"Giao lộ / góc đường"** cho R3.
- Nhắc mọi người: phân vân thì bấm **L (Khó)**. Ở pilot gần như không ai bấm.

## Ảnh ví dụ

- `guide/examples_v1_consensus.jpg`: ảnh được cả nhóm, hoặc 4/5 người, đồng ý.
- Lưu ý ảnh 3 và ảnh 6 ở hàng "Bị chặn": vật cản nằm ở đoạn xa. Theo R1 thì hai ảnh này **có thể đổi thành 0**. Nhóm quyết trong buổi họp.
- Sau buổi họp, chọn 2–3 ảnh mẫu cho mỗi quy tắc R1–R6.
