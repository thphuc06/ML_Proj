# Hướng dẫn gán nhãn vỉa hè, v0 (dùng cho pilot)

**Câu hỏi duy nhất:** Trên đoạn vỉa hè nhìn thấy trong ảnh, người đi bộ có phải **bước xuống lòng đường** mới đi tiếp được không?

Mọi ảnh là **vỉa hè phía bên phải xe chụp**, nhìn chếch về phía trước, nên đoạn vỉa hè chạy từ gần (dưới trái) ra xa (giữa ảnh). Chỉ xét **vỉa hè gần nhất ở phía ảnh nhìn tới**. Không xét vỉa hè bên kia đường, cũng không đoán đoạn nằm ngoài khung hình.

## 3 lựa chọn

| Phím | Nhãn | Khi nào chọn |
|---|---|---|
| **A** | **0 – Còn lối đi** | Còn **một dải mặt vỉa hè liên tục, không bị chắn**, chạy suốt đoạn thấy trong ảnh. Một người lớn đi qua được, có thể phải né nhẹ, mà không cần bước xuống lòng đường. Xe máy đậu sát mép nhưng vẫn chừa lối thì vẫn là 0. Nhãn này **không** có nghĩa là vỉa hè đạt chuẩn độ rộng. |
| **S** | **1 – Bị chặn** | Có vật cản **chắn ngang toàn bộ lối đi** ở ít nhất một chỗ trong đoạn thấy được, không còn dải trống liên tục. Ví dụ: hàng xe máy đậu kín, hàng hóa, quầy hàng, bàn ghế quán, ô tô đậu trên vỉa hè, rào chắn, công trình. **Chỉ thấy có xe hay có quán thì chưa đủ** để chọn 1. |
| **D** | **Không đủ thông tin** | Ảnh **không đủ bằng chứng** để trả lời câu hỏi, và **bắt buộc chọn lý do** (phím F G H J K). Vỉa hè **bị phủ kín bởi vật cản** thì chọn **1**, không chọn mục này. Ảnh khó nhưng vẫn nhìn thấy thì vẫn chọn 0 hoặc 1. |

**Lý do "Không đủ thông tin":**
- **F** Không thấy vỉa hè gần: ảnh chỉ thấy lòng đường, dải phân cách hoặc vỉa hè bên kia.
- **G** Ảnh mờ, quá tối, hoặc khung hình lệch.
- **H** Phần quyết định bị che: xe buýt, xe tải, người chụp che mất.
- **J** Phía này không có vỉa hè: mặt tiền sát đường, công trường, cầu.
- **K** Lý do khác (ghi chú lại để họp pilot).

## Quy tắc tạm cho ca khó (sẽ chốt sau pilot)

- **Người hoặc xe đang di chuyển** không tính là vật cản. **Xe đang đậu**, không có người lái, thì tính.
- **Lối vào nhà, ram dốc, lối vào cây xăng** cắt ngang vỉa hè không tính là chặn, trừ khi có vật đậu chắn trên đó.
- **Cây, cột điện, bồn cây, tủ điện** tính là chặn **chỉ khi** không còn dải trống nào để đi qua.
- **Lối hẹp:** còn đi thẳng được bằng một người thì là 0. Phải nghiêng người, lách sát xe hoặc bước lên đồ vật thì là 1.
- Phân vân **quá 5 giây** thì vẫn chọn nhãn mình nghiêng về, và bấm **L = "Khó / không chắc"**.

## Thông tin phụ (không bắt buộc)

- **Vật cản thấy được** (chọn nhiều): Q xe máy đậu · W ô tô đậu · E hàng hóa / quầy hàng · R bàn ghế quán · T rào chắn / công trình · Y khác.
- **L = Khó / không chắc.**

## Cách làm trên Label Studio

**Bố trí phím:** hàng giữa theo thứ tự thao tác: **A S D** (nhãn) → **F G H J K** (lý do khi chọn D) → **L** (khó). Hàng trên **Q W E R T Y** là vật cản. Nộp: **Ctrl + Enter**.

> **Tắt bộ gõ tiếng Việt** (Unikey/EVKey chuyển sang **E**) khi gán nhãn để phím tắt không bị bộ gõ chặn.
>
> **Bấm lại cùng một phím sẽ bỏ chọn.** Chọn nhầm thì bấm thẳng phím của lựa chọn đúng.

1. Đăng nhập địa chỉ Label Studio của nhóm và mở **đúng project mang tên mình**: `PILOT_<tên>`. **Không mở project của người khác.**
2. Bấm **Label All Tasks**.
3. Với mỗi ảnh: bấm **A**, **S** hoặc **D**. Nếu chọn D thì bấm thêm lý do (F G H J K). Chọn vật cản hoặc cờ "Khó" nếu có. Bấm **Submit** (Ctrl + Enter).
4. **Không trao đổi về ảnh với nhau** cho đến khi cả nhóm gán xong pilot. Pilot đo mức đồng thuận độc lập, trao đổi trước sẽ làm sai kết quả.
5. Có thể dừng giữa chừng; lần sau mở lại sẽ gán tiếp từ ảnh chưa làm.

*Ảnh: © Mapillary contributors, CC BY-SA 4.0. Phần làm mờ mặt người và biển số giữ nguyên.*
