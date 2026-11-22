# Photo quality gate

`predict.py` checks the photo before it is classified (`photo_quality`). It works on the
same copy the model sees (shorter side 256) and returns `quality`:

| check | rule | threshold |
|---|---|---|
| too_dark | mean grey level (0 to 255) below | 40 |
| too_blurry | variance of the Laplacian of the grey image below | 15 |
| no_leaf | share of leaf coloured pixels (HSV hue 10 to 90, sat >= 40, val >= 30) below | 0.05 |

Checks run in that order and the first one that fails is returned. Anything other than
`ok` sets `uncertain` to true. `no_leaf` also skips severity (`severity_band` is `no_leaf`).
Thresholds live in `configs/thresholds.json` under `quality_gate`.

## How the thresholds were picked

Stats on the real test photos (test_field, 623 photos):

- mean grey: 1st percentile 73, median 137
- Laplacian variance: 1st percentile 28, median 280
- leaf colour share: only 1 photo under 0.05, 12 under 0.10

The leaf mask from `severity.py` was tried first for the no_leaf check, but it is empty on
more than 5% of real field leaves, so a looser colour share is used instead.

Each threshold sits under the 1st percentile of real photos. To check that the gate does
catch bad photos, the test_field photos were also changed on purpose:

| set | ok | too_dark | too_blurry | no_leaf |
|---|---|---|---|---|
| test_field (real) | 620 | 0 | 2 | 1 |
| test_lab (real, 1135) | 1127 | 6 | 1 | 1 |
| test_field darkened x0.2 | 1 | 619 | 3 | 0 |
| test_field darkened x0.3 | 169 | 288 | 109 | 57 |
| test_field Gaussian blur sigma 3 | 0 | 0 | 623 | 0 |
| test_field Gaussian blur sigma 2 | 24 | 0 | 599 | 0 |
| test_field turned to greyscale (stand in for no leaf) | 0 | 0 | 2 | 621 |

So about 0.5% of real field photos get flagged (a false retake request), and strong dark or
blur is almost always caught. Mildly dark photos (x0.3) are only partly caught; we kept the
dark threshold low on purpose because the model still works on many of them. The 6 lab
photos marked too_dark have very dark backgrounds.

Limits: we have no real non leaf photos (soil, hands, sky), so the no_leaf check is only
tested with greyscale copies. Green background such as grass will pass as a leaf.
