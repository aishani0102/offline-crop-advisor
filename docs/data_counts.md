# Data counts

Written by `detection/data/build_dataset.py`. These are the real counts after de-duplication and balancing. Plan and reasons are in `docs/DATASETS.md`.

## Cleaning

- images found: 23903
- unreadable, skipped: 0
- near-duplicates removed (phash distance <= 4): 795
- duplicate groups that span two or more sources: 58
- images dropped because copies had different labels: 175
- duplicates removed, by source: {'plantdoc': 26, 'plantseg': 54, 'plantvillage': 54, 'pld': 75, 'potato_ethiopia': 19, 'potato_indonesia': 43, 'tomato_village': 524}
- label-conflict images dropped, by source: {'plantdoc': 61, 'plantseg': 48, 'pld': 60, 'tomato_village': 6}
- images found, by source: {'plantdoc': 801, 'plantseg': 680, 'plantvillage': 14732, 'pld': 4072, 'potato_ethiopia': 430, 'potato_indonesia': 548, 'tomato_village': 2640}
- images left after cleaning: 22933
- split fingerprint (sha256, first 16): 09129439436a1ece

## Images per class and split

`unused` is what balancing left out of train (over the 700 field or 1,000 total cap).

| class | train | val | test_field | test_lab | unused |
|---|---|---|---|---|---|
| potato_early_blight | 1000 | 261 | 172 | 100 | 1157 |
| potato_healthy | 822 | 169 | 209 | 15 | 468 |
| potato_late_blight | 1000 | 292 | 235 | 100 | 1298 |
| tomato_early_blight | 1000 | 172 | 85 | 100 | 148 |
| tomato_healthy | 1000 | 148 | 30 | 158 | 518 |
| tomato_late_blight | 1000 | 207 | 113 | 190 | 1165 |
| tomato_leaf_miner | 700 | 202 | 104 | 0 | 13 |
| tomato_leaf_mold | 899 | 115 | 24 | 95 | 0 |
| tomato_septoria_leaf_spot | 1000 | 125 | 27 | 177 | 663 |
| tomato_yellow_leaf_curl_virus | 1000 | 109 | 21 | 200 | 4127 |
| total | 9421 | 1800 | 1020 | 1135 | 9557 |

## train by source

| class | plantvillage | plantdoc | plantseg | tomato_village | potato_indonesia | potato_ethiopia | pld | total |
|---|---|---|---|---|---|---|---|---|
| potato_early_blight | 300 | 75 | 36 | 0 | 0 | 0 | 589 | 1000 |
| potato_healthy | 122 | 0 | 0 | 0 | 140 | 241 | 319 | 822 |
| potato_late_blight | 300 | 77 | 44 | 0 | 214 | 47 | 318 | 1000 |
| tomato_early_blight | 652 | 58 | 78 | 212 | 0 | 0 | 0 | 1000 |
| tomato_healthy | 802 | 49 | 0 | 149 | 0 | 0 | 0 | 1000 |
| tomato_late_blight | 445 | 81 | 77 | 397 | 0 | 0 | 0 | 1000 |
| tomato_leaf_miner | 0 | 0 | 0 | 700 | 0 | 0 | 0 | 700 |
| tomato_leaf_mold | 761 | 74 | 64 | 0 | 0 | 0 | 0 | 899 |
| tomato_septoria_leaf_spot | 831 | 116 | 53 | 0 | 0 | 0 | 0 | 1000 |
| tomato_yellow_leaf_curl_virus | 902 | 58 | 40 | 0 | 0 | 0 | 0 | 1000 |

## val by source

| class | plantvillage | plantdoc | plantseg | tomato_village | potato_indonesia | potato_ethiopia | pld | total |
|---|---|---|---|---|---|---|---|---|
| potato_early_blight | 100 | 8 | 5 | 0 | 0 | 0 | 148 | 261 |
| potato_healthy | 15 | 0 | 0 | 0 | 20 | 34 | 100 | 169 |
| potato_late_blight | 100 | 9 | 6 | 0 | 30 | 7 | 140 | 292 |
| tomato_early_blight | 100 | 6 | 14 | 52 | 0 | 0 | 0 | 172 |
| tomato_healthy | 100 | 6 | 0 | 42 | 0 | 0 | 0 | 148 |
| tomato_late_blight | 100 | 9 | 12 | 86 | 0 | 0 | 0 | 207 |
| tomato_leaf_miner | 0 | 0 | 0 | 202 | 0 | 0 | 0 | 202 |
| tomato_leaf_mold | 95 | 8 | 12 | 0 | 0 | 0 | 0 | 115 |
| tomato_septoria_leaf_spot | 100 | 13 | 12 | 0 | 0 | 0 | 0 | 125 |
| tomato_yellow_leaf_curl_virus | 100 | 6 | 3 | 0 | 0 | 0 | 0 | 109 |

## test_field by source

| class | plantdoc | plantseg | tomato_village | potato_indonesia | potato_ethiopia | pld | total |
|---|---|---|---|---|---|---|---|
| potato_early_blight | 6 | 8 | 0 | 0 | 0 | 158 | 172 |
| potato_healthy | 0 | 0 | 0 | 40 | 69 | 100 | 209 |
| potato_late_blight | 5 | 17 | 0 | 61 | 13 | 139 | 235 |
| tomato_early_blight | 9 | 29 | 47 | 0 | 0 | 0 | 85 |
| tomato_healthy | 8 | 0 | 22 | 0 | 0 | 0 | 30 |
| tomato_late_blight | 10 | 19 | 84 | 0 | 0 | 0 | 113 |
| tomato_leaf_miner | 0 | 0 | 104 | 0 | 0 | 0 | 104 |
| tomato_leaf_mold | 6 | 18 | 0 | 0 | 0 | 0 | 24 |
| tomato_septoria_leaf_spot | 11 | 16 | 0 | 0 | 0 | 0 | 27 |
| tomato_yellow_leaf_curl_virus | 6 | 15 | 0 | 0 | 0 | 0 | 21 |

## test_lab by source

| class | plantvillage | total |
|---|---|---|
| potato_early_blight | 100 | 100 |
| potato_healthy | 15 | 15 |
| potato_late_blight | 100 | 100 |
| tomato_early_blight | 100 | 100 |
| tomato_healthy | 158 | 158 |
| tomato_late_blight | 190 | 190 |
| tomato_leaf_miner | 0 | 0 |
| tomato_leaf_mold | 95 | 95 |
| tomato_septoria_leaf_spot | 177 | 177 |
| tomato_yellow_leaf_curl_virus | 200 | 200 |

## train field vs lab

| class | field | lab |
|---|---|---|
| potato_early_blight | 700 | 300 |
| potato_healthy | 700 | 122 |
| potato_late_blight | 700 | 300 |
| tomato_early_blight | 348 | 652 |
| tomato_healthy | 198 | 802 |
| tomato_late_blight | 555 | 445 |
| tomato_leaf_miner | 700 | 0 |
| tomato_leaf_mold | 138 | 761 |
| tomato_septoria_leaf_spot | 169 | 831 |
| tomato_yellow_leaf_curl_virus | 98 | 902 |
