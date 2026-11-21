# Severity baseline against PlantSeg lesion masks

Command: `python -I detection/severity.py --eval-plantseg --root <data_root>`

Our lesion mask comes from HSV colour rules (see `detection/severity.py`). We compare it
with the hand-drawn PlantSeg lesion masks on every tomato and potato disease image in
PlantSeg (813 images, including two tomato diseases outside our class list). The colour
thresholds were picked on 220 PlantSeg train images, so the test split is the fair number.

| PlantSeg split | images | mean IoU | mean Dice |
|---|---|---|---|
| train (thresholds picked here) | 563 | 0.176 | 0.273 |
| val | 90 | 0.181 | 0.279 |
| test | 160 | 0.194 | 0.298 |
| all | 813 | 0.180 | 0.279 |

Only 4 percent of images reach IoU above 0.5. The lesion area we find barely tracks
the real lesion area (Pearson r = 0.08 over all images). Virus classes are the worst
(leaf curl virus IoU 0.03, mosaic 0.04), which makes sense: they show up as yellowing and
curling, not as spots.

Honest summary: this baseline is not good enough to tell mild from severe on its own.
It treats any non-green part of the leaf as lesion, so shadows, glare, yellowing and
brown background inside the leaf outline all count. PlantSeg has no leaf masks, so our
leaf area, and therefore the severity percentage itself, cannot be checked directly.

Phase 2 plan: train a small segmentation model (U-Net with a MobileNet encoder, or
DeepLabV3 with MobileNetV3) on the PlantSeg lesion masks, plus a leaf mask model or
a leaf mask from a second class, and export it with ExecuTorch like the classifier.

Per-image numbers are in `severity_plantseg_per_image.csv`, the summary in `severity_plantseg.json`.
