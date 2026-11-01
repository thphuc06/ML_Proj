# Hướng dẫn gán nhãn vỉa hè, v1 (dự thảo)

Cần tra nhanh khi gán thì xem [bảng tra nhanh](bang_tra_nhanh.jpg). Bản này thay cho v0 sau khi nhóm họp xong. Những chỗ ghi **(chờ họp)** là đề xuất, nhóm sẽ chốt trong buổi họp.

## Việc cần làm

Mỗi ảnh chụp **vỉa hè phía bên phải xe chụp**, nhìn chếch về phía trước. Bạn trả lời một câu hỏi:

> Người đi bộ có phải bước xuống lòng đường mới đi tiếp được dọc đoạn vỉa hè này không?

Chỉ đánh giá những gì thấy trong ảnh, tại thời điểm chụp. Không đoán phần ngoài khung hình.

## Vài từ cần hiểu giống nhau

- **Vỉa hè gần:** đoạn vỉa hè nằm cùng phía với ảnh đang nhìn, ngay cạnh làn đường xe chụp đang chạy. Vỉa hè bên kia đường không tính.
- **Mép vỉa hè:** đường ranh giữa vỉa hè và lòng đường, thường là bó vỉa (gờ đá cao hơn mặt đường).
- **Vạch 3/5:** một vạch ngang tưởng tượng ở vị trí 3/5 chiều cao ảnh, tính từ trên xuống. Trong các ảnh ví dụ đây là **đường màu xanh**. Ảnh trên Label Studio không có vạch này, bạn ước lượng bằng mắt: thấp hơn giữa ảnh một chút.
- **Lối đi liên tục:** một đường đi không bị đứt, một người đi thẳng qua được.

## Ba lựa chọn

| Phím | Lựa chọn | Nghĩa |
|---|---|---|
| A | **Còn lối đi** (nhãn 0) | Thấy vỉa hè gần, và một người đi thẳng qua được suốt đoạn đó |
| S | **Bị chặn** (nhãn 1) | Thấy vỉa hè gần, nhưng có chỗ không đi qua được |
| D | **Không đủ thông tin** | Ảnh không cho phép trả lời câu hỏi. Bấm thêm lý do |

## Cách quyết định: trả lời lần lượt 3 câu

### Câu 1. Ảnh có xem được không?

Ảnh cháy sáng, tối hoặc mờ tới mức không nhận ra mặt vỉa hè: chọn **Không đủ thông tin**, lý do **Ảnh mờ / tối / cháy sáng**.

### Câu 2. Có thấy vỉa hè gần không?

Nhìn mép vỉa hè. **Mép vỉa hè có đoạn nào nằm dưới vạch 3/5 không?**

- **Không:** chọn **Không đủ thông tin**, lý do **Không thấy vỉa hè**. Gặp lý do này khi:
  - ảnh chủ yếu là lòng đường, vỉa hè chỉ là một dải mỏng ở xa;
  - phía này không có vỉa hè;
  - ảnh chụp giữa giao lộ, chỉ thấy vạch qua đường hoặc góc đường;
  - ảnh chụp một sân rộng, không có đoạn vỉa hè chạy dọc.
- **Có:** xem tiếp xe hoặc người ở sát camera có che mất vỉa hè không.
  - Che **quá nửa** đoạn vỉa hè gần: chọn **Không đủ thông tin**, lý do **Bị che**.
  - Che ít hơn: sang câu 3, xét phần còn thấy.

### Câu 3. Có còn lối đi liên tục không?

Dùng mắt lần theo một đường đi dọc vỉa hè, từ gần ra xa.

- Một người **đi thẳng qua được**, không phải nghiêng người, lách, hoặc bước xuống lòng đường: chọn **Còn lối đi**.
- Có **một chỗ** không qua được: chọn **Bị chặn**, rồi chọn loại vật cản.

Quan trọng nhất: hỏi **"còn đi được không"**, đừng hỏi "có nhiều xe không". Vỉa hè rộng có nhiều xe vẫn có thể còn lối đi. Một đống gạch nhỏ ở vỉa hè hẹp vẫn có thể chặn hẳn.

## Tình huống hay gặp

| Tình huống | Chọn |
|---|---|
| Xe máy hoặc ô tô đậu sát mặt tiền, vẫn chừa dải đi sát mép đường | Còn lối đi |
| Hàng hóa bày sát cửa hàng, mặt vỉa hè phía ngoài còn trống | Còn lối đi |
| Cột điện, cây, tủ điện, nhưng vẫn còn chỗ đi | Còn lối đi |
| Người đang đi, đang dắt xe, hoặc xe đang chạy trên vỉa hè | Còn lối đi nếu không có vật cản khác, vì chúng chỉ ở đó tạm thời |
| Lối vào nhà, ram dốc cắt ngang vỉa hè | Còn lối đi, nếu không có gì đậu chắn |
| Hàng xe đậu kín bề ngang vỉa hè | Bị chặn |
| Gạch đá, xe đẩy, quầy hàng, bàn ghế chiếm hết bề ngang ở một chỗ | Bị chặn |
| Vỉa hè phủ kín xe hoặc hàng tới mức không thấy mặt vỉa hè | **Bị chặn**, không chọn Không đủ thông tin |
| Vỉa hè hỏng, mặt bê tông thô, nhưng vẫn đi được | Còn lối đi. Chất lượng mặt vỉa hè không thuộc phạm vi đề tài |

**(Chờ họp)**
- Vật cản ở xa tới đâu thì không tính nữa. Đề xuất: chỉ tính phần còn nhận ra từng chiếc xe, khoảng tới giữa ảnh.
- Lối hẹp bao nhiêu thì tính là chặn. Đề xuất: không đi thẳng qua được thì chặn. Bề ngang xe máy, khoảng 0,7 m, chỉ dùng để ước lượng bằng mắt.
- Xe đậu rải rác có khe giữa các xe. Đề xuất: khe đi thẳng qua được thì còn lối đi.
- Người đứng hoặc ngồi trên vỉa hè. Đề xuất: người không tính, bàn ghế và xe thì tính.
- Ô tô đậu trước cổng. Đề xuất: xét như vật cản khác.

## Lý do khi chọn "Không đủ thông tin"

| Phím | Lý do | Khi nào chọn |
|---|---|---|
| F | **Không thấy vỉa hè** | Vỉa hè quá xa, phía này không có vỉa hè, giao lộ, sân rộng |
| G | **Ảnh mờ / tối / cháy sáng** | Chất lượng ảnh không đủ để nhận ra mặt vỉa hè |
| H | **Bị che** | Xe hoặc người sát camera che quá nửa đoạn vỉa hè gần |
| J | **Lý do khác** | Không thuộc 3 lý do trên, và ghi chú lại |

Bản v0 có hai lý do riêng là "Không thấy vỉa hè gần" và "Phía này không có vỉa hè". Trong pilot hai lý do này bị dùng lẫn cho cùng ảnh, nên v1 gộp lại.

## Thông tin phụ

- **Vật cản (Q W E R T Y):** xe máy đậu · ô tô đậu · hàng hóa, quầy hàng · bàn ghế quán · rào chắn, công trình · khác. **(Chờ họp)** Đề xuất: chỉ chọn khi nhãn là Bị chặn, và bắt buộc chọn ít nhất một loại.
- **L – Khó / không chắc:** bấm khi phân vân quá 5 giây. Vẫn phải chọn nhãn bạn nghiêng về.
- **Ghi chú:** ghi lại khi gặp ca lạ. Thông tin này giúp sửa guide.

## Cách thao tác

1. Tắt bộ gõ tiếng Việt (chuyển Unikey hoặc EVKey sang E).
2. Mở **đúng project mang tên mình**, bấm **Label All Tasks**.
3. Bấm A, S hoặc D. Nếu chọn D thì bấm thêm F, G, H hoặc J.
4. Bấm **Ctrl + Enter** để nộp.
5. Bấm lại cùng một phím sẽ bỏ chọn. Chọn nhầm thì bấm thẳng phím đúng.
6. Không trao đổi về ảnh với nhau trong lúc gán.

*Ảnh: © Mapillary contributors, CC BY-SA 4.0. Phần làm mờ mặt người và biển số giữ nguyên.*
