# Rà soát pilot trước buổi họp thống nhất

Nhóm sẽ họp để thống nhất cách gán rồi mới gán chính thức. Tài liệu này ghi lại kết quả pilot, chỉ ra nhóm đang chấm khác nhau ở đâu, và đề xuất cách gán cho từng loại ảnh.

Lúc gán nhãn chỉ cần xem [bảng tra nhanh](guide/bang_tra_nhanh.jpg). Tài liệu này dành cho buổi họp.

Cách dùng trong buổi họp: đọc mục 1–3 để nắm tình hình, rồi dành phần lớn thời gian cho mục 5.

- Số liệu pilot giữ nguyên, không sửa nhãn của ai.
- Các nhãn đề xuất là góc nhìn của Claude để cả nhóm thảo luận. **Nhãn cuối do nhóm quyết.**

**Cách đọc ảnh ví dụ:**

- **Ảnh #52** là số thứ tự của ảnh trong [danh sách ảnh cần xem](../data/labels/pilot_report/pilot_review_items.csv).
- Dòng vàng là đề xuất cách gán. Dòng "Phiếu" cho biết trong 5 người có bao nhiêu người đã chọn mỗi đáp án.
- **Đường màu xanh** là vạch 3/5 chiều cao ảnh, xem mục 3. Vạch này chỉ có trong ảnh ví dụ, không có trên Label Studio.

## 1. Kết quả pilot

5 người gán độc lập cùng 150 ảnh.

| Chỉ số | Kết quả |
|---|---|
| Đồng thuận chung, trên cả 3 lựa chọn | **0,57**, chưa đạt ngưỡng 0,6 |
| Đồng thuận về việc ảnh có đủ thông tin không | 0,65 |
| Đồng thuận về "còn lối đi" hay "bị chặn" (82 ảnh cả 5 người coi là đủ thông tin) | **0,49** |
| Số ảnh 5/5 người đồng ý | 77 |
| Số ảnh 4/5 người đồng ý | 38 |
| Số ảnh từ 3/5 người trở xuống | 35 |
| Theo đa số | Còn lối đi 82 · Không đủ thông tin 44 · Bị chặn 19 · không có đa số 5 |

Chỉ số đồng thuận ở đây là Fleiss κ: 1 là hoàn toàn giống nhau, 0 là giống nhau không hơn gì chọn ngẫu nhiên. Ngưỡng 0,6 là mức nhóm đã đặt để bắt đầu gán chính thức.

## 2. Nhóm đang chấm khác nhau ở đâu

### Theo người

So sánh mỗi người với 4 người còn lại. Đây là khác biệt về cách hiểu, **không có nghĩa ai đúng ai sai**.

| Người | Tỉ lệ chấm "Bị chặn" | Xu hướng so với 4 người còn lại |
|---|---|---|
| Loan | 8% | Dễ tính nhất. Trong 21 ảnh 4 người kia chấm "Bị chặn", Loan chấm "Còn lối đi" 14 ảnh |
| Khải | 12% | Ở khoảng giữa |
| Học | 15% | Ở khoảng giữa |
| Phúc | 16% | Ở khoảng giữa, sát nhóm nhất: giống đa số 89% số ảnh |
| Minh | 25% | Khó tính nhất. Trong 84 ảnh 4 người kia chấm "Còn lối đi", Minh chấm "Bị chặn" 15 ảnh và "Không đủ thông tin" 12 ảnh |

Hai thói quen khác cũng cần thống nhất:

- **Chọn vật cản:** Minh và Phúc chỉ chọn vật cản ở ảnh "Bị chặn". Học, Khải, Loan chọn cả ở ảnh "Còn lối đi" (21%, 42%, 54% số ảnh đó).
- **Cờ "Khó":** gần như không ai bấm (tối đa 1%), và không có ghi chú nào.

### Theo loại ảnh

73 ảnh không được cả 5 người đồng ý, chia thành 8 nhóm. Cột cuối là mức đồng thuận **cao nhất có thể** nếu nhóm thống nhất hoàn toàn riêng loại ảnh đó, xuất phát từ 0,57. Đây là mức trần, không phải kết quả dự kiến.

| Loại ảnh | Số ảnh | Đồng thuận cao nhất có thể |
|---|---|---|
| Vỉa hè ở xa, ảnh chủ yếu là lòng đường | 18 | 0,67 |
| Xe hoặc hàng chiếm một phần vỉa hè | 18 | 0,67 |
| Xe, người che ở sát camera | 8 | 0,63 |
| Giao lộ, góc đường, sân rộng | 10 | 0,63 |
| Ảnh thông thoáng nhưng có người chấm khác | 11 | 0,62 |
| Bị chặn rõ nhưng có người chấm khác | 4 | 0,60 |
| Xe, người dừng tạm | 2 | 0,58 |
| Ảnh cháy sáng | 2 | 0,58 |

**Hai loại đầu là ưu tiên của buổi họp.** Thống nhất được cả hai thì đồng thuận có thể lên tối đa khoảng 0,77.

## 3. Đề xuất cách gán

Hướng dẫn đầy đủ nằm ở [guide v1](guide/annotation_guide_v1_draft.md). Tóm tắt: trả lời lần lượt 3 câu, gặp đáp án là dừng.

**Câu 1. Ảnh có xem được không?** Cháy sáng hoặc mờ tới mức không nhận ra mặt vỉa hè thì chọn *Không đủ thông tin*, lý do *Ảnh mờ / tối / cháy sáng*.

**Câu 2. Có thấy vỉa hè gần không?** Tưởng tượng một vạch ngang ở **3/5 chiều cao ảnh tính từ trên xuống**, tức thấp hơn giữa ảnh một chút. Mép vỉa hè là ranh giới giữa vỉa hè và lòng đường.

- Mép vỉa hè không có đoạn nào nằm dưới vạch: *Không đủ thông tin*, lý do *Không thấy vỉa hè*.
- Có, nhưng xe hoặc người sát camera che quá nửa đoạn vỉa hè gần: *Không đủ thông tin*, lý do *Bị che*.
- Có, và che ít hơn: sang câu 3.

**Câu 3. Còn lối đi liên tục không?** Lần theo một đường đi dọc vỉa hè.

- Một người đi thẳng qua được, không nghiêng, không lách, không bước xuống lòng đường: *Còn lối đi*.
- Có một chỗ không qua được: *Bị chặn*, rồi chọn vật cản.

**Quan trọng nhất: hỏi "còn đi được không", đừng hỏi "có nhiều xe không".** Ảnh #21 và #26 có nhiều xe nhưng vẫn còn lối đi. Ảnh #13 ít vật cản nhưng bị chắn hẳn.

### Gộp lý do "Không đủ thông tin"

Bản v0 có hai lý do "Không thấy vỉa hè gần" và "Phía này không có vỉa hè". Đề xuất **gộp thành một lý do "Không thấy vỉa hè"**, bao gồm luôn giao lộ và sân rộng. Dự thảo trước định thêm lý do "Giao lộ", nay bỏ.

Lý do gộp, theo số liệu pilot:

- 19 ảnh từng được chọn "Phía này không có vỉa hè", thì 18 ảnh cũng có người chọn "Không thấy vỉa hè gần" cho chính ảnh đó.
- Không ảnh nào được mọi người thống nhất riêng lý do "Phía này không có vỉa hè".
- Gộp lại, mức đồng ý về lý do tăng từ 79% lên 90%.

Sau khi gộp còn 4 lý do: **Không thấy vỉa hè · Ảnh mờ / tối / cháy sáng · Bị che · Lý do khác.**

## 4. Ví dụ theo từng loại ảnh

### Vỉa hè ở xa

Hàng trên: mép vỉa hè nằm trên đường xanh, ảnh chủ yếu là lòng đường. Hàng dưới: mép vỉa hè xuống tới đường xanh hoặc thấp hơn, nên xét tiếp. Ảnh #62 và #69 sát vạch, là các ca khó phân định bằng mắt.

![Vỉa hè ở xa](guide/review/1_vi_he_xa.jpg)

### Giao lộ, sân rộng

Không có đoạn vỉa hè chạy dọc để xét, nên chọn *Không thấy vỉa hè*. Ảnh #49 có dải vỉa hè nhỏ bên phải và 3/5 người chấm "Còn lối đi", nên để nhóm quyết.

![Giao lộ và sân rộng](guide/review/2_giao_lo.jpg)

### Bị che ở sát camera

Hàng trên: xe che mất đoạn gần. Hàng dưới: xe hoặc người che ít, vỉa hè vẫn thấy, nên xét tiếp.

![Bị che](guide/review/3_bi_che.jpg)

### Còn lối đi dù có vật cản

Các ảnh này có xe hoặc hàng, nhưng vẫn còn đường đi thẳng qua.

![Còn lối đi](guide/review/4_con_loi_di.jpg)

### Bị chặn

Có ít nhất một chỗ không qua được.

![Bị chặn](guide/review/5_bi_chan.jpg)

### Dừng tạm và vật cố định

Người và xe đang di chuyển chỉ ở đó tạm thời. Cột, tủ điện không chắn hết lối.

![Tạm thời và thông thoáng](guide/review/6_tam_thoi_thong_thoang.jpg)

## 5. Những câu nhóm cần chốt

| # | Câu hỏi | Đề xuất | Cơ sở |
|---|---|---|---|
| 1 | Vỉa hè phải thấp tới đâu mới tính là thấy? | Mép vỉa hè xuống dưới vạch 3/5 | **Đã đo:** khớp đa số nhóm 89%, kiểm tra chéo 86% |
| 2 | Có gộp lý do thành "Không thấy vỉa hè" không? | Gộp, kể cả giao lộ và sân rộng | **Đã đo:** xem mục 3 |
| 3 | Vật cản ở xa tới đâu thì không tính? | Chỉ tính phần còn nhận ra từng chiếc xe, khoảng tới giữa ảnh | Quy ước, dữ liệu chưa phân biệt được |
| 4 | Lối hẹp bao nhiêu thì tính là chặn? | Không đi thẳng qua được thì chặn. Bề ngang xe máy, khoảng 0,7 m, chỉ để ước lượng bằng mắt | Quy ước, chưa đo được từ ảnh |
| 5 | Xe đậu rải rác có khe giữa các xe thì sao? | Khe đi thẳng qua được thì còn lối đi | Xem ảnh #1, #11 |
| 6 | Người đứng hoặc ngồi trên vỉa hè có tính không? | Người không tính, bàn ghế và xe thì tính | Xem ảnh #10, #12 |
| 7 | Ô tô đậu trước cổng thì sao? | Xét như vật cản khác | Xem ảnh #17 |
| 8 | Khi nào chọn vật cản? | Chỉ khi chọn "Bị chặn", và bắt buộc chọn ít nhất một loại | Để trường này có nghĩa rõ là nguyên nhân chặn |

Các ảnh cần nhóm tự xem và quyết:

![Cần họp quyết](guide/review/7_can_hop_quyet.jpg)

## 6. Đề xuất nào đáng tin tới đâu

- **Đã đo được:** mốc 3/5 chiều cao ảnh, việc gộp lý do, xu hướng khác nhau của từng người, thứ tự ưu tiên các loại ảnh.
- **Chưa đo được:** câu 3 và câu 4 ở mục 5. Công cụ đo trên ảnh không dự đoán được phiếu của nhóm, nên đây là quy ước nhóm tự chọn, cần kiểm tra lại ở vòng 50 ảnh.
- **Giới hạn:** pilot chỉ có 150 ảnh và 19 ảnh "Bị chặn" theo đa số. Đồng thuận cao chỉ cho thấy nhóm gán nhất quán, không chứng minh nhãn đúng.

## 7. Sau buổi họp

1. Chốt các câu ở mục 5, cập nhật guide v1, chọn ảnh mẫu.
2. Chốt nhãn cuối cho 35 ảnh có từ 3/5 phiếu trở xuống.
3. Cập nhật giao diện gán nhãn trên Label Studio.
4. Cả nhóm gán vòng kiểm tra 50 ảnh mới. Đạt đồng thuận từ 0,6 trở lên thì bắt đầu gán chính thức.
