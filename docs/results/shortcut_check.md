# Shortcut check: is the model reading the disease or the dataset?

Model: MobileNetV3-Large FP32 (the Colab run, see `training.md`).
Command: `python -I detection/shortcut_check.py --root <data_root> --tag mnv3_large_fp32_pytorch`.
It reuses the predictions saved by `evaluate.py`, so nothing is re-run.

The worry: several classes come mostly from one source. Field potato_healthy comes only
from the Indonesia and Ethiopia sets, and tomato_leaf_miner only from Tomato-Village. A
model can score well by learning what a source looks like (camera, background, light)
instead of what the disease looks like.

## Accuracy per source on the field test set

| source | images | accuracy | crop known accuracy |
|---|---|---|---|
| PlantDoc | 61 | 0.738 | 0.787 |
| PlantSeg | 122 | 0.795 | 0.836 |
| Potato Ethiopia | 82 | 1.000 | 1.000 |
| Potato Indonesia | 101 | 0.990 | 0.990 |
| Tomato-Village | 257 | 0.973 | 0.973 |

This is the main finding. On the three sources where every photo was taken by one team in
one place (Tomato-Village, Indonesia, Ethiopia), accuracy is 97 to 100 percent. On the two
web-scraped sources (PlantDoc and PlantSeg), which mix many cameras and places, it is 74
to 80 percent. Our headline field accuracy of 0.921 is lifted by the easy single-source
sets, which make up 440 of the 623 field test images. **The PlantDoc plus PlantSeg number
(about 0.78 over 183 images) is the better guess for photos from a new farm.**

Part of the single-source score is probably near-copies too: photos from the same field
and the same day look alike, even when they are not close enough to be caught by our
duplicate check (pHash within 4 bits).

## Correct / images, per class and source

| class | PlantDoc | PlantSeg | Ethiopia | Indonesia | Tomato-Village |
|---|---|---|---|---|---|
| potato_early_blight | 2/6 | 6/8 | | | |
| potato_healthy | | | 69/69 | 39/40 | |
| potato_late_blight | 5/5 | 14/17 | 13/13 | 61/61 | |
| tomato_early_blight | 9/9 | 18/29 | | | 46/47 |
| tomato_healthy | 3/8 | | | | 18/22 |
| tomato_late_blight | 7/10 | 17/19 | | | 84/84 |
| tomato_leaf_miner | | | | | 102/104 |
| tomato_leaf_mold | 5/6 | 14/18 | | | |
| tomato_septoria_leaf_spot | 9/11 | 14/16 | | | |
| tomato_yellow_leaf_curl_virus | 5/6 | 14/15 | | | |

Tomato healthy is a clear case: 18/22 on Tomato-Village but 3/8 on PlantDoc.

## Potato healthy against the two blights

Field test, plain top class:

| true \ predicted | early blight | healthy | late blight | a tomato class |
|---|---|---|---|---|
| potato_early_blight (14) | 8 | 0 | 3 | 3 |
| potato_healthy (109) | 0 | 108 | 1 | 0 |
| potato_late_blight (96) | 2 | 0 | 93 | 1 |

What speaks against a pure source shortcut: Ethiopia and Indonesia each have both healthy and
late blight photos, and the model separates them inside each source (Ethiopia 69/69 healthy and
13/13 blight, Indonesia 39/40 healthy and 61/61 blight). So it is not just saying "Indonesian
photo, so healthy". Also, no PlantDoc or PlantSeg potato blight photo (36 images) was called
healthy.

The lab test is the other cross-source check. All 15 PlantVillage potato_healthy lab test photos
are called potato_healthy, even though most of our field healthy potato photos come from two
farms. All 100 lab early blight photos are right, and 98 of the 100 lab late blight photos (the
other 2 are called tomato_late_blight).

What we cannot check: there is no field photo of a healthy potato leaf from any source other than
Indonesia and Ethiopia. So we do not know how a healthy potato from an Indian field would do. Potato
early blight is also weak in the field (8 of 14 right), and those are the only 14 field test images.

## Leaf miner

- Leaf miner is right on 102 of 104 field test images, all from Tomato-Village.
- Of the 153 other Tomato-Village test images, only 4 are called leaf miner, and the other
  Tomato-Village classes are 96.7 percent right. So inside Tomato-Village the model tells leaf miner
  apart from early blight, late blight and healthy. It is not calling every Tomato-Village photo leaf miner.
- No image from another source is called leaf miner. But no other source has leaf miner at all, so
  this tells us nothing about how a leaf miner photo from another farm would do.

So the 0.98 recall is real for Tomato-Village style photos but is an untested claim for anything else.

## What to do next

1. Report the web-source field accuracy (about 0.78) next to the headline 0.92.
2. Get a few dozen of our own phone photos (or other clearly licensed photos) of leaf miner,
   healthy potato and potato early blight from a different place, and use them only as a test set.
3. Grouping near-same photos by place and day before splitting would make the single-source test
   numbers fairer, but the sources do not give that information, so it would need hand checking.
