# Data counts

Written by `detection/data/build_dataset.py`. These are the real counts after de-duplication and balancing. Plan and reasons are in `docs/DATASETS.md`.

## Cleaning

- images found: 19831
- unreadable, skipped: 0
- near-duplicates removed (phash distance <= 4): 720
- duplicate groups that span two or more sources: 58
- images dropped because copies had different labels: 115
- duplicates removed, by source: {'plantdoc': 26, 'plantseg': 54, 'plantvillage': 54, 'potato_ethiopia': 19, 'potato_indonesia': 43, 'tomato_village': 524}
- label-conflict images dropped, by source: {'plantdoc': 61, 'plantseg': 48, 'tomato_village': 6}
- images found, by source: {'plantdoc': 801, 'plantseg': 680, 'plantvillage': 14732, 'potato_ethiopia': 430, 'potato_indonesia': 548, 'tomato_village': 2640}
- images left after cleaning: 18996
- split fingerprint (sha256, first 16): 6d440b3fd40706b6

## Images per class and split

`unused` is what balancing left out of train (over the 700 field or 1,000 total cap).

| class | train | val | test_field | test_lab | unused |
|---|---|---|---|---|---|
| potato_early_blight | 909 | 113 | 14 | 100 | 0 |
| potato_healthy | 503 | 69 | 109 | 15 | 0 |
| potato_late_blight | 1000 | 152 | 96 | 100 | 181 |
| tomato_early_blight | 1000 | 172 | 85 | 100 | 148 |
| tomato_healthy | 1000 | 148 | 30 | 158 | 518 |
| tomato_late_blight | 1000 | 207 | 113 | 190 | 1165 |
| tomato_leaf_miner | 700 | 202 | 104 | 0 | 13 |
| tomato_leaf_mold | 899 | 115 | 24 | 95 | 0 |
| tomato_septoria_leaf_spot | 1000 | 125 | 27 | 177 | 663 |
| tomato_yellow_leaf_curl_virus | 1000 | 109 | 21 | 200 | 4127 |
| total | 9011 | 1412 | 623 | 1135 | 6815 |

## train by source

| class | plantvillage | plantdoc | plantseg | tomato_village | potato_indonesia | potato_ethiopia | total |
|---|---|---|---|---|---|---|---|
| potato_early_blight | 798 | 75 | 36 | 0 | 0 | 0 | 909 |
| potato_healthy | 122 | 0 | 0 | 0 | 140 | 241 | 503 |
| potato_late_blight | 618 | 77 | 44 | 0 | 214 | 47 | 1000 |
| tomato_early_blight | 652 | 58 | 78 | 212 | 0 | 0 | 1000 |
| tomato_healthy | 802 | 49 | 0 | 149 | 0 | 0 | 1000 |
| tomato_late_blight | 445 | 81 | 77 | 397 | 0 | 0 | 1000 |
| tomato_leaf_miner | 0 | 0 | 0 | 700 | 0 | 0 | 700 |
| tomato_leaf_mold | 761 | 74 | 64 | 0 | 0 | 0 | 899 |
| tomato_septoria_leaf_spot | 831 | 116 | 53 | 0 | 0 | 0 | 1000 |
| tomato_yellow_leaf_curl_virus | 902 | 58 | 40 | 0 | 0 | 0 | 1000 |

## val by source

| class | plantvillage | plantdoc | plantseg | tomato_village | potato_indonesia | potato_ethiopia | total |
|---|---|---|---|---|---|---|---|
| potato_early_blight | 100 | 8 | 5 | 0 | 0 | 0 | 113 |
| potato_healthy | 15 | 0 | 0 | 0 | 20 | 34 | 69 |
| potato_late_blight | 100 | 9 | 6 | 0 | 30 | 7 | 152 |
| tomato_early_blight | 100 | 6 | 14 | 52 | 0 | 0 | 172 |
| tomato_healthy | 100 | 6 | 0 | 42 | 0 | 0 | 148 |
| tomato_late_blight | 100 | 9 | 12 | 86 | 0 | 0 | 207 |
| tomato_leaf_miner | 0 | 0 | 0 | 202 | 0 | 0 | 202 |
| tomato_leaf_mold | 95 | 8 | 12 | 0 | 0 | 0 | 115 |
| tomato_septoria_leaf_spot | 100 | 13 | 12 | 0 | 0 | 0 | 125 |
| tomato_yellow_leaf_curl_virus | 100 | 6 | 3 | 0 | 0 | 0 | 109 |

## test_field by source

| class | plantdoc | plantseg | tomato_village | potato_indonesia | potato_ethiopia | total |
|---|---|---|---|---|---|---|
| potato_early_blight | 6 | 8 | 0 | 0 | 0 | 14 |
| potato_healthy | 0 | 0 | 0 | 40 | 69 | 109 |
| potato_late_blight | 5 | 17 | 0 | 61 | 13 | 96 |
| tomato_early_blight | 9 | 29 | 47 | 0 | 0 | 85 |
| tomato_healthy | 8 | 0 | 22 | 0 | 0 | 30 |
| tomato_late_blight | 10 | 19 | 84 | 0 | 0 | 113 |
| tomato_leaf_miner | 0 | 0 | 104 | 0 | 0 | 104 |
| tomato_leaf_mold | 6 | 18 | 0 | 0 | 0 | 24 |
| tomato_septoria_leaf_spot | 11 | 16 | 0 | 0 | 0 | 27 |
| tomato_yellow_leaf_curl_virus | 6 | 15 | 0 | 0 | 0 | 21 |

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
| potato_early_blight | 111 | 798 |
| potato_healthy | 381 | 122 |
| potato_late_blight | 382 | 618 |
| tomato_early_blight | 348 | 652 |
| tomato_healthy | 198 | 802 |
| tomato_late_blight | 555 | 445 |
| tomato_leaf_miner | 700 | 0 |
| tomato_leaf_mold | 138 | 761 |
| tomato_septoria_leaf_spot | 169 | 831 |
| tomato_yellow_leaf_curl_virus | 98 | 902 |
