# Train enrichment labels: report

Export: `data/labels/raw/train_extra_export_20261112_1825` (gitignored). Projects `MAIN2_*`, one annotator per crop.
Labelled: 2000/2000 assigned crops; missing 0; unknown label value 0; tasks saved more than once 0 (latest kept).

## 1. Strata

| group     |   crops |   0 |   1 |   I |   blocked/crop | 95% CI         |   blocked/usable |   I share |
|:----------|--------:|----:|----:|----:|---------------:|:---------------|-----------------:|----------:|
| all       |    2000 | 810 | 588 | 602 |          0.294 | [0.274, 0.314] |            0.421 |     0.301 |
| top_score |    1400 | 479 | 541 | 380 |          0.386 | [0.361, 0.412] |            0.53  |     0.271 |
| random    |     600 | 331 |  47 | 222 |          0.078 | [0.059, 0.103] |            0.124 |     0.37  |

- Pool: 5035 crops. Top stratum = all 1400 crops with score >= 0.610; random stratum = 600 of the other 3635.
- Estimated blocked share of the whole pool (what random labelling would find): **0.164** [0.148, 0.182].
- Blocked share of the 2,000 labelled crops: **0.294**, i.e. **1.8x** random labelling of the same pool (588 blocked against about 328).
- Top stratum vs random stratum: 0.386 vs 0.078.
- Recall of the top stratum over the pool's blocked crops: 0.66 [0.595, 0.724] (the top 28% of the pool).
- On the 10 old train streets (benchmark, leave-one-street-out): 70/30 rule at 36-40% of the pool gave about 0.13 blocked per crop; random 0.058.

## 2. Blocked share by score band

| group         |   crops |   0 |   1 |   I |   blocked/crop | 95% CI         |   blocked/usable |   I share |
|:--------------|--------:|----:|----:|----:|---------------:|:---------------|-----------------:|----------:|
| (-0.001, 0.2] |     308 | 191 |   6 | 111 |          0.019 | [0.009, 0.042] |            0.03  |     0.36  |
| (0.2, 0.4]    |     165 |  82 |  16 |  67 |          0.097 | [0.061, 0.152] |            0.163 |     0.406 |
| (0.4, 0.61]   |     129 |  58 |  26 |  45 |          0.202 | [0.141, 0.279] |            0.31  |     0.349 |
| (0.61, 0.7]   |     341 | 160 |  87 |  94 |          0.255 | [0.212, 0.304] |            0.352 |     0.276 |
| (0.7, 0.8]    |     361 | 157 | 118 |  86 |          0.327 | [0.281, 0.377] |            0.429 |     0.238 |
| (0.8, 0.9]    |     364 | 108 | 156 | 100 |          0.429 | [0.379, 0.480] |            0.591 |     0.275 |
| (0.9, 1.0]    |     332 |  54 | 179 |  99 |          0.539 | [0.485, 0.592] |            0.768 |     0.298 |

Bands below 0.61 hold only random-stratum crops; bands above hold only top-stratum crops.

## 3. Road type

| group       |   crops |   0 |   1 |   I |   blocked/crop | 95% CI         |   blocked/usable |   I share |
|:------------|--------:|----:|----:|----:|---------------:|:---------------|-----------------:|----------:|
| primary     |     207 | 109 |  47 |  51 |          0.227 | [0.175, 0.289] |            0.301 |     0.246 |
| residential |     189 |  38 |  62 |  89 |          0.328 | [0.265, 0.398] |            0.62  |     0.471 |
| secondary   |     374 | 176 |  99 |  99 |          0.265 | [0.223, 0.312] |            0.36  |     0.265 |
| tertiary    |    1230 | 487 | 380 | 363 |          0.309 | [0.284, 0.335] |            0.438 |     0.295 |

Within the random stratum only (no selection by score):

| group       |   crops |   0 |   1 |   I |   blocked/crop | 95% CI         |   blocked/usable |   I share |
|:------------|--------:|----:|----:|----:|---------------:|:---------------|-----------------:|----------:|
| primary     |      70 |  40 |   3 |  27 |          0.043 | [0.015, 0.119] |            0.07  |     0.386 |
| residential |      38 |  15 |   4 |  19 |          0.105 | [0.042, 0.241] |            0.211 |     0.5   |
| secondary   |     108 |  62 |   5 |  41 |          0.046 | [0.020, 0.104] |            0.075 |     0.38  |
| tertiary    |     384 | 214 |  35 | 135 |          0.091 | [0.066, 0.124] |            0.141 |     0.352 |

## 4. Streets

Pool-weighted blocked share per street (top-stratum count + random-stratum rate x the street's other crops), streets with >= 3 random crops: 62. Spearman with the street scan score: **0.55** (p = 0.000). Few random crops per street, so each value is rough.

| street_id            | highway     |   scan_score |   labelled |   blocked |   random_crops |   est_pool_blocked |
|:---------------------|:------------|-------------:|-----------:|----------:|---------------:|-------------------:|
| Nguyễn Duy#0         | tertiary    |        0.456 |         18 |        11 |              4 |              0.557 |
| Dương Tử Giang       | tertiary    |        0.495 |         15 |         7 |              3 |              0.551 |
| Nguyễn Thái Bình#0   | tertiary    |        0.516 |         36 |        20 |             10 |              0.421 |
| Ung Văn Khiêm        | secondary   |        0.526 |         28 |        16 |              5 |              0.396 |
| Cống Quỳnh#0         | secondary   |        0.412 |         16 |         5 |              3 |              0.327 |
| Ba Đình#1            | tertiary    |        0.508 |         26 |        11 |              5 |              0.314 |
| Ba Đình#0            | residential |        0.385 |         23 |         7 |             10 |              0.302 |
| Hòa Hảo#0            | residential |        0.431 |         14 |         5 |              4 |              0.298 |
| Vạn Kiếp#0           | tertiary    |        0.574 |         26 |         9 |              5 |              0.286 |
| Bùi Đình Tuý#0       | tertiary    |        0.491 |         43 |        14 |              5 |              0.284 |
| Nguyễn Thượng Hiền#1 | tertiary    |        0.621 |         30 |        13 |              5 |              0.277 |
| Tùng Thiện Vương     | primary     |        0.436 |         20 |        12 |              3 |              0.261 |
| Vĩnh Khánh           | tertiary    |        0.525 |         18 |         6 |              6 |              0.248 |
| Hoàng Hoa Thám       | tertiary    |        0.637 |         46 |        16 |              8 |              0.239 |
| Triệu Quang Phục     | tertiary    |        0.317 |         14 |         6 |              9 |              0.235 |

Lowest:

| street_id         | highway     |   scan_score |   labelled |   blocked |   random_crops |   est_pool_blocked |
|:------------------|:------------|-------------:|-----------:|----------:|---------------:|-------------------:|
| Lê Hồng Phong#1   | secondary   |        0.466 |         21 |         3 |              8 |              0.055 |
| Nguyễn Biểu       | secondary   |        0.374 |         15 |         2 |              7 |              0.045 |
| Dương Bá Trạc     | primary     |        0.416 |         18 |         2 |              5 |              0.044 |
| Đào Duy Từ#0      | residential |        0.321 |         13 |         2 |              7 |              0.043 |
| Thành Thái        | secondary   |        0.286 |         39 |         4 |             12 |              0.034 |
| Trần Huy Liệu     | tertiary    |        0.317 |         12 |         1 |              7 |              0.025 |
| Ngô Gia Tự#1      | primary     |        0.307 |         11 |         1 |              9 |              0.018 |
| Nguyễn Công Trứ#0 | tertiary    |        0.283 |         12 |         0 |              5 |              0     |

## 5. Annotators

| annotator   |   crops |   zero |   one |   insufficient |   median_s |   difficult |   blocked/crop |   blocked/crop random stratum |
|:------------|--------:|-------:|------:|---------------:|-----------:|------------:|---------------:|------------------------------:|
| Hoc         |     400 |    148 |   173 |             79 |        3.8 |       0     |          0.432 |                         0.148 |
| Khai        |     400 |    181 |   125 |             94 |        3.9 |       0.028 |          0.312 |                         0.076 |
| Loan        |     400 |    184 |    76 |            140 |        6.8 |       0.025 |          0.19  |                         0.008 |
| Minh        |     400 |    151 |   101 |            148 |        3.8 |       0.222 |          0.252 |                         0.078 |
| Phuc        |     400 |    146 |   113 |            141 |        3.1 |       0.005 |          0.282 |                         0.088 |

Crops were assigned at random, so large differences between annotators point at different reading of the guide, not at different images.

## 6. Reasons and obstacles

Reasons given for Không đủ thông tin: Không thấy vỉa hè 463, Bị che 106, Ảnh mờ / tối / cháy sáng 21, Lý do khác 9, (none) 3

Obstacles on blocked crops: Xe máy đậu 351, Hàng hóa / quầy hàng 221, Khác 66, Bàn ghế quán 49, Rào chắn / công trình 38, Ô tô đậu 11, (none) 3

Obstacles tagged on crops labelled 0: 112 of 810.

Notes: 2.
