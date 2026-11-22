# Shortcut check: is the model reading the disease or the dataset?

Model: MobileNetV3-Large FP32 (see `training.md`). INT8 per-source numbers are in the last table.
Command: `python -I detection/shortcut_check.py --root <data_root> --tag mnv3_large_fp32_pytorch`.
It reuses the predictions saved by `evaluate.py`, so nothing is re-run.

The worry: several classes come mostly from one source. Field potato_healthy comes only
from the PLD, Indonesia and Ethiopia sets, and tomato_leaf_miner only from Tomato-Village. A
model can score well by learning what a source looks like (camera, background, light)
instead of what the disease looks like.

## Accuracy per source on the field test set

| source | images | accuracy | crop known accuracy |
|---|---|---|---|
| PlantDoc | 61 | 0.738 | 0.787 |
| PlantSeg | 122 | 0.844 | 0.869 |
| PLD (Punjab potato) | 397 | 0.992 | 0.992 |
| Potato Ethiopia | 82 | 0.988 | 0.988 |
| Potato Indonesia | 101 | 0.990 | 0.990 |
| Tomato-Village | 257 | 0.969 | 0.969 |

This is the main finding. On the four sources where every photo was taken by one team in
one place (PLD, Tomato-Village, Indonesia, Ethiopia), accuracy is 97 to 99 percent. On the two
web-scraped sources (PlantDoc and PlantSeg), which mix many cameras and places, it is 74
to 84 percent. Our headline field accuracy of 0.953 is lifted by the easy single-source
sets, which make up 837 of the 1,020 field test images. **The PlantDoc plus PlantSeg number
(0.809 over 183 images, 0.765 for INT8) is the better guess for photos from a new farm.**

Part of the single-source score is probably near-copies too: photos from the same field
and the same day look alike, even when they are not close enough to be caught by our
duplicate check (pHash within 4 bits).

## Correct / images, per class and source

| class | PlantDoc | PlantSeg | PLD | Ethiopia | Indonesia | Tomato-Village |
|---|---|---|---|---|---|---|
| potato_early_blight | 2/6 | 6/8 | 155/158 | | | |
| potato_healthy | | | 100/100 | 68/69 | 39/40 | |
| potato_late_blight | 5/5 | 14/17 | 139/139 | 13/13 | 61/61 | |
| tomato_early_blight | 9/9 | 21/29 | | | | 45/47 |
| tomato_healthy | 3/8 | | | | | 18/22 |
| tomato_late_blight | 6/10 | 17/19 | | | | 83/84 |
| tomato_leaf_miner | | | | | | 103/104 |
| tomato_leaf_mold | 5/6 | 16/18 | | | | |
| tomato_septoria_leaf_spot | 10/11 | 14/16 | | | | |
| tomato_yellow_leaf_curl_virus | 5/6 | 15/15 | | | | |

Tomato healthy is a clear case: 18/22 on Tomato-Village but 3/8 on PlantDoc. Potato early
blight is 155/158 on PLD but 8/14 on the web sources.

## Potato healthy against the two blights

Field test, plain top class:

| true \ predicted | early blight | healthy | late blight | a tomato class |
|---|---|---|---|---|
| potato_early_blight (172) | 163 | 2 | 4 | 3 |
| potato_healthy (209) | 0 | 207 | 2 | 0 |
| potato_late_blight (235) | 2 | 0 | 232 | 1 |

What speaks against a pure source shortcut: PLD, Ethiopia and Indonesia each have healthy and
blight photos, and the model separates them inside each source (PLD 100/100 healthy, 155/158 early
blight, 139/139 late blight; Ethiopia 68/69 healthy and 13/13 blight; Indonesia 39/40 healthy and
61/61 blight). So it is not just saying "photo from this farm, so healthy". Also, no PlantDoc or
PlantSeg potato blight photo (36 images) was called healthy.

The lab test is the other cross-source check. All 15 PlantVillage potato_healthy lab test photos
are called potato_healthy. All 100 lab early blight photos are right, and 98 of the 100 lab late
blight photos (the other 2 are called tomato_late_blight).

What we cannot check: healthy potato field photos come from three single-team sets (Punjab,
Indonesia, Ethiopia); none is from an Indian field. Web-source potato early blight is weak (8 of 14).

## Leaf miner

- Leaf miner is right on 103 of 104 field test images, all from Tomato-Village.
- Of the 153 other Tomato-Village test images, 5 are called leaf miner, and the other
  Tomato-Village classes are 95.4 percent right. So inside Tomato-Village the model tells leaf miner
  apart from early blight, late blight and healthy. It is not calling every Tomato-Village photo leaf miner.
- No image from another source is called leaf miner. But no other source has leaf miner at all, so
  this tells us nothing about how a leaf miner photo from another farm would do.

So the 0.99 recall is real for Tomato-Village style photos but is an untested claim for anything else.

## INT8 (the shipped file), accuracy per source

`--tag mnv3_large_int8_pte`:

| source | images | accuracy | crop known accuracy |
|---|---|---|---|
| PlantDoc | 61 | 0.705 | 0.770 |
| PlantSeg | 122 | 0.795 | 0.828 |
| PLD (Punjab potato) | 397 | 0.982 | 0.987 |
| Potato Ethiopia | 82 | 0.988 | 0.988 |
| Potato Indonesia | 101 | 0.980 | 0.980 |
| Tomato-Village | 257 | 0.938 | 0.938 |

## What to do next

1. Report the web-source field accuracy (0.81 FP32, 0.77 INT8) next to the headline 0.95.
2. Get a few dozen of our own phone photos (or other clearly licensed photos) of leaf miner,
   healthy potato and potato early blight from an Indian field, and use them only as a test set.
3. Grouping near-same photos by place and day before splitting would make the single-source test
   numbers fairer, but the sources do not give that information, so it would need hand checking.
