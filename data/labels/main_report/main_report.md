# Main labelling report (11/11/2026)

Export: `data/labels/raw/main_export_20261111` (gitignored). Annotations: 4435/4435 assigned slots, 0 missing, 3 task(s) saved twice (latest kept).

## Per annotator

| annotator   |   n |   share0 |   share1 |   shareI |   median_s |   under_2s |   difficult |   notes |
|:------------|----:|---------:|---------:|---------:|-----------:|-----------:|------------:|--------:|
| Hoc         | 887 |     0.69 |     0.1  |     0.21 |       2.06 |       0.48 |        0    |       0 |
| Khai        | 887 |     0.52 |     0.08 |     0.39 |       3.4  |       0.27 |        0    |       0 |
| Loan        | 887 |     0.54 |     0.06 |     0.4  |       5.89 |       0    |        0    |       0 |
| Minh        | 887 |     0.45 |     0.05 |     0.5  |       2.35 |       0.43 |        0.12 |       1 |
| Phuc        | 887 |     0.47 |     0.06 |     0.47 |       7.47 |       0.15 |        0.04 |       0 |

## Agreement on double-labelled items

| group | pair | n | raw agree | κ 3-way | κ binary | n binary |
|---|---|---|---|---|---|---|
| test | Hoc–Loan | 674 | 79% | 0.60 | 0.68 | 418 |
| train (cross 15%) | Hoc–Minh | 14 | 64% | 0.33 | -0.12 | 9 |
| train (cross 15%) | Khai–Phuc | 17 | 71% | 0.35 | 0.00 | 11 |
| train (cross 15%) | Minh–Hoc | 12 | 75% | 0.40 | 0.00 | 9 |
| train (cross 15%) | Minh–Khai | 12 | 92% | 0.85 | 0.55 | 5 |
| train (cross 15%) | Minh–Loan | 13 | 92% | 0.84 | nan | 5 |
| train (cross 15%) | Minh–Phuc | 16 | 81% | 0.64 | nan | 5 |
| train (cross 15%) | Phuc–Hoc | 39 | 72% | 0.51 | 0.36 | 27 |
| train (cross 15%) | Phuc–Khai | 48 | 75% | 0.54 | 1.00 | 21 |
| train (cross 15%) | Phuc–Loan | 22 | 82% | 0.66 | 0.70 | 7 |
| train (cross 15%) | Phuc–Minh | 41 | 85% | 0.71 | 1.00 | 24 |
| val | Minh–Khai | 486 | 80% | 0.64 | 0.55 | 211 |
| **test, all** | | 674 | 79% | **0.60** | 0.68 | 418 |
| **train (cross 15%), all** | | 276 | 78% | **0.61** | 0.56 | 144 |
| **val, all** | | 486 | 80% | **0.64** | 0.55 | 211 |

## Label pairs on double-labelled items (unordered)

| grp               |   0/0 |   0/1 |   0/I |   1/1 |   1/I |   I/I |
|:------------------|------:|------:|------:|------:|------:|------:|
| test              |   362 |    25 |    94 |    31 |    24 |   138 |
| train (cross 15%) |   121 |    13 |    38 |    10 |    10 |    84 |
| val               |   174 |    21 |    61 |    16 |    17 |   197 |

## Provisional label per item (disagreements open)

|                       |    0 |   1 |   ? |    I |   All |
|:----------------------|-----:|----:|----:|-----:|------:|
| ('test', 'agreed')    |  362 |  31 |   0 |  138 |   531 |
| ('test', 'disagree')  |    0 |   0 | 143 |    0 |   143 |
| ('train', 'agreed')   |  121 |  10 |   0 |   84 |   215 |
| ('train', 'disagree') |    0 |   0 |  61 |    0 |    61 |
| ('train', 'single')   |  803 |  88 |   0 |  672 |  1563 |
| ('val', 'agreed')     |  174 |  16 |   0 |  197 |   387 |
| ('val', 'disagree')   |    0 |   0 |  99 |    0 |    99 |
| ('All', '')           | 1460 | 145 | 303 | 1091 |  2999 |

## Blocked (1) per split, before adjudication

| split | items | agreed or single 1 | open with a 1 vote | 1 if every open item went to 1 |
|---|---|---|---|---|
| test | 674 | 31 | 49 | 80 |
| train | 1839 | 98 | 23 | 121 |
| val | 486 | 16 | 38 | 54 |

## After adjudication (303 items: proposal by eye, 28 changed by Phuc)

| split   |    0 |   1 |    I |   All |
|:--------|-----:|----:|-----:|------:|
| test    |  412 |  47 |  215 |   674 |
| train   |  939 | 106 |  794 |  1839 |
| val     |  207 |  35 |  244 |   486 |
| All     | 1558 | 188 | 1253 |  2999 |

| split | blocked | usable (0/1) | blocked share of usable |
|---|---|---|---|
| test | 47 | 459 | 10.2% |
| train | 106 | 1045 | 10.1% |
| val | 35 | 242 | 14.5% |

## Insufficient reasons (v0 names mapped to v1)

| reason                   |   count |
|:-------------------------|--------:|
| Không thấy vỉa hè        |    1434 |
| Bị che                   |     270 |
| Ảnh mờ / tối / cháy sáng |      38 |
| Lý do khác               |       7 |
| (missing)                |       5 |

## Blocked labels without an obstacle tag

| annotator   | obstacles   |
|:------------|:------------|
| Hoc         | 0/88        |
| Khai        | 3/74        |
| Loan        | 6/53        |
| Minh        | 0/45        |
| Phuc        | 10/52       |

## Labels by street (all annotations)

|                                    |    0 |    1 |    I |
|:-----------------------------------|-----:|-----:|-----:|
| ('test', 'Hai Bà Trưng')           | 0.68 | 0.1  | 0.23 |
| ('test', 'Lý Thường Kiệt')         | 0.7  | 0.04 | 0.26 |
| ('test', 'Nơ Trang Long')          | 0.65 | 0.12 | 0.23 |
| ('test', 'Trần Phú')               | 0.33 | 0.14 | 0.53 |
| ('train', 'Cách Mạng Tháng Tám#0') | 0.6  | 0.09 | 0.31 |
| ('train', 'Hải Thượng Lãn Ông')    | 0.26 | 0.17 | 0.57 |
| ('train', 'Lê Văn Sỹ')             | 0.77 | 0.1  | 0.13 |
| ('train', 'Nguyễn Kiệm#0')         | 0.4  | 0.07 | 0.53 |
| ('train', 'Nguyễn Thị Minh Khai')  | 0.54 | 0.03 | 0.42 |
| ('train', 'Nguyễn Trãi')           | 0.46 | 0.05 | 0.49 |
| ('train', 'Pasteur')               | 0.18 | 0.01 | 0.81 |
| ('train', 'Phan Đăng Lưu')         | 0.69 | 0.07 | 0.24 |
| ('train', 'Trần Hưng Đạo')         | 0.63 | 0.05 | 0.32 |
| ('train', 'Điện Biên Phủ#1')       | 0.42 | 0.04 | 0.54 |
| ('val', 'Hồng Bàng')               | 0.42 | 0.09 | 0.49 |
| ('val', 'Nguyễn Đình Chiểu#0')     | 0.42 | 0.04 | 0.54 |
| ('val', 'Võ Văn Tần')              | 0.53 | 0.12 | 0.36 |