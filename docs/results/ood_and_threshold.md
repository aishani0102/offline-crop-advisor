# Out-of-scope photos and the "uncertain" threshold

Model: `mnv3_large_int8.pte` (INT8, temperature T = 0.687), run exactly like `detection/predict.py`
(quality gate, then 10 logits). Script: `python -I detection/ood_threshold.py --root <data_root>
--model <data_root>/models/mnv3_large_pld/mnv3_large_int8.pte --ood <data_root>/raw/plantvillage_ood`.

- In-domain: val split (1,800 photos, used to tune) and field test (1,020 photos, report only),
  scored with their true crop as the farmer's choice.
- Out-of-scope (OOD): 325 PlantVillage leaf photos of 14 other crops (apple, corn, grape, pepper,
  soybean, strawberry, ...; 13 per class, `pick.txt`), each scored twice: as "tomato" and as
  "potato" (650 cases). No non-plant photos: we found none with a clear offline licence, so
  this set only tests "a leaf of the wrong plant".

## The current rule lets most wrong-plant photos through

Quality gate + crop-restricted top probability only:

| threshold | crop chosen | quality gate rejects | confidence rejects | confident diagnosis |
|---|---|---|---|---|
| 0.52 | tomato | 0.003 | 0.505 | 0.492 |
| 0.52 | potato | 0.003 | 0.268 | 0.729 |
| 0.60 | tomato | 0.003 | 0.603 | 0.394 |
| 0.60 | potato | 0.003 | 0.425 | 0.572 |
| 0.70 | tomato | 0.003 | 0.714 | 0.283 |
| 0.70 | potato | 0.003 | 0.588 | 0.409 |
| 0.80 | tomato | 0.003 | 0.831 | 0.166 |
| 0.80 | potato | 0.003 | 0.695 | 0.302 |

The quality gate catches 1 of 325 (they are sharp, bright, green leaves). Restricting the
softmax to one crop hides the problem: if a corn leaf looks most like potato_healthy among the
three potato classes, it gets a high potato probability even when the model's full 10-class
output never pointed at potato.

## Which score separates wrong-plant photos best

Val (quality ok) against OOD (quality ok). "OOD passed" is the share of OOD cases above the
cutoff that keeps 95% or 98% of val photos.

| score (from the 10 logits) | AUROC | OOD passed at 95% val kept | OOD passed at 98% val kept |
|---|---|---|---|
| crop-restricted top prob (current) | 0.930 | 0.384 | 0.613 |
| max softmax over all 10 classes | 0.938 | 0.352 | 0.534 |
| energy, -T logsumexp(logits/T) | 0.950 | 0.256 | 0.417 |
| **chosen crop's probability mass** | **0.962** | **0.185** | **0.356** |

Crop mass is best and is free to compute. Grid on val (coverage / answered accuracy / OOD answered):

| crop mass >= | top >= 0.52 | top >= 0.56 | top >= 0.60 | top >= 0.70 |
|---|---|---|---|---|
| none | 0.974 / 0.9681 / 0.611 | 0.966 / 0.9724 / 0.545 | 0.958 / 0.9762 / 0.483 | 0.938 / 0.9805 / 0.346 |
| 0.7 | 0.961 / 0.9699 / 0.263 | 0.954 / 0.9744 / 0.251 | 0.948 / 0.9777 / 0.229 | 0.929 / 0.9815 / 0.182 |
| 0.8 | 0.952 / 0.9702 / 0.206 | **0.944 / 0.9747 / 0.197** | 0.939 / 0.9775 / 0.185 | 0.921 / 0.9813 / 0.152 |
| 0.9 | 0.922 / 0.9723 / 0.117 | 0.917 / 0.9764 / 0.115 | 0.912 / 0.9793 / 0.112 | 0.896 / 0.9833 / 0.103 |

## Threshold sweep (with crop mass >= 0.8)

Coverage = share of in-domain photos answered. Wrong caught = share of photos the model gets
wrong that are flagged uncertain. OOD answered = share of the 650 wrong-plant cases given a
confident diagnosis.

| threshold | val coverage | val answered acc | val wrong caught | field coverage | field answered acc | field wrong caught | OOD answered (tomato / potato) |
|---|---|---|---|---|---|---|---|
| 0.40 | 0.963 | 0.9642 | 0.195 | 0.956 | 0.9487 | 0.153 | 0.249 (0.394 / 0.105) |
| 0.44 | 0.962 | 0.9648 | 0.208 | 0.953 | 0.9516 | 0.203 | 0.232 (0.360 / 0.105) |
| 0.48 | 0.958 | 0.9664 | 0.247 | 0.951 | 0.9526 | 0.220 | 0.222 (0.338 / 0.105) |
| 0.52 | 0.952 | 0.9702 | 0.338 | 0.944 | 0.9533 | 0.237 | 0.206 (0.308 / 0.105) |
| **0.56** | **0.944** | **0.9747** | **0.442** | **0.936** | **0.9581** | **0.322** | **0.197 (0.289 / 0.105)** |
| 0.60 | 0.939 | 0.9775 | 0.506 | 0.925 | 0.9629 | 0.407 | 0.185 (0.265 / 0.105) |
| 0.64 | 0.933 | 0.9774 | 0.506 | 0.913 | 0.9678 | 0.492 | 0.177 (0.249 / 0.105) |
| 0.68 | 0.926 | 0.9796 | 0.558 | 0.911 | 0.9699 | 0.525 | 0.162 (0.218 / 0.105) |
| 0.72 | 0.918 | 0.9819 | 0.610 | 0.904 | 0.9707 | 0.542 | 0.149 (0.197 / 0.102) |
| 0.76 | 0.907 | 0.9859 | 0.701 | 0.895 | 0.9715 | 0.559 | 0.134 (0.166 / 0.102) |
| 0.80 | 0.898 | 0.9864 | 0.714 | 0.881 | 0.9755 | 0.627 | 0.125 (0.148 / 0.102) |

Every 0.02 step, and the same sweep without the mass rule, is printed by the script. Without the crop mass rule, 0.52 answers 61% of
wrong-plant cases and 0.60 still answers 48%.

## Decision

Rule used to choose, on val plus OOD only: val answered accuracy >= 97% and val coverage >= 94%,
then the lowest OOD answered rate. That gives **top prob
>= 0.56 and crop mass >= 0.8**.

- **Is 0.52 sensible?** Not on its own: with the top prob alone, 0.52 has val answered accuracy
  96.8% (under 97%) and gives a confident diagnosis to 61% of wrong-plant photos. With the crop
  mass rule, 0.52 would be acceptable (97.0%, OOD 21%), but 0.56 catches 10 more points of the
  model's own mistakes (44% vs 34% on val) for under 1 point of coverage, so we use 0.56.
- Field test at the chosen rule: 93.6% answered, 95.8% of answered photos right, 32% of wrong
  ones caught; per source the answered accuracy is PLD 0.990, Ethiopia 0.988, Indonesia 0.979,
  Tomato-Village 0.959, PlantSeg 0.860, PlantDoc 0.800.
- Still open: about 1 in 5 wrong-plant leaves (29% when the farmer picks tomato, 11% potato)
  get a confident answer. The app text should say it only knows tomato and potato.

## Exact app rule (Kotlin computes the same from the 10 logits)

```
z_i   = logits_i / T                              T = 0.687 (from mnv3_large_meta.json)
p_i   = exp(z_i) / sum_j exp(z_j)                 over all 10 classes
mass  = sum of p_i over the chosen crop's classes
top   = max over the chosen crop's classes of p_i / mass   (= crop-restricted softmax)
uncertain_reason =
    quality            if quality != "ok"
    "not_crop"         else if mass < 0.80
    "low_confidence"   else if top  < 0.56
    none               otherwise
uncertain = (uncertain_reason != none)
```

Values are in `configs/thresholds.json` (`uncertain_below_confidence`, `ood.min_crop_mass`);
`predict.py` now also returns `uncertain_reason` and `crop_mass`.
