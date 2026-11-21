# Grad-CAM on field test photos

Made with `detection/gradcam.py` on the final model (`mnv3_large_cont/best.pt`), Grad-CAM on
the last conv block. Left is the photo as the model sees it (224 center crop), right is the
heat map (red = parts that pushed the predicted class up most, blue = little effect).

We took the three weakest classes on the field test set and, for each, the first photo the
model gets right and the first one it gets wrong.

| class | right | wrong |
|---|---|---|
| potato_early_blight | `potato_early_blight_right.png` | `potato_early_blight_wrong.png` (said late blight) |
| tomato_healthy | `tomato_healthy_right.png` | `tomato_healthy_wrong.png` (said leaf mold) |
| tomato_early_blight | `tomato_early_blight_right.png` | `tomato_early_blight_wrong.png` (said leaf mold) |

What we see:

- On the correct ones the model looks at the leaf itself: the brown spots on the potato
  leaf, and the leaf blades and veins on the healthy tomato. It does not look at the
  black background or the watermark.
- Potato early blight wrong: the photo has many leaves and the heat is on one leaf with a
  large dry brown patch, which does look like late blight. Several small target spots on
  other leaves are ignored. A close photo of one leaf would likely help.
- Tomato healthy wrong: a pile of cut leaves on a table with strong blue/cyan colour cast.
  The heat is weak and mostly on the wooden table in the corner, not on a leaf. Colour cast
  plus background is enough to confuse it, so the quality gate does not catch this case
  (the photo is bright, sharp and has green).
- Tomato early blight wrong: the heat is on the brown spots, so it looks at the right
  place, but it reads them as leaf mold. These two look alike in low light.
- Tomato early blight right: this "field" photo is really a slide with printed text, and
  the heat is on the diseased leaf, not the text. Good, but it shows the field test set
  has some web images that are not real phone photos.

These are 6 photos only, so this shows the kind of mistake, not how often it happens.
