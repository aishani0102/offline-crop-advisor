# Known limits of the detection side

Short list of what the numbers do not show, for the report.

1. **Field accuracy is flattered by easy sources.** The shortcut check
   (`shortcut_check.md`) splits the field test set by source. On sets taken in one place with
   one camera (PLD, Tomato-Village, Indonesia, Ethiopia) accuracy is 97 to 99 percent. On the
   web-scraped sets (PlantDoc, PlantSeg), which are closer to random farmer photos, it is 74
   to 84 percent, 0.81 overall (0.77 for INT8). The headline field accuracy of 0.953 (0.932
   INT8) should always be shown next to this.

2. **Severity is a rough baseline.** It is a colour threshold method, not a trained
   segmenter. On PlantSeg test images the lesion mask has mean IoU 0.19 against the real
   masks, only 4 percent of images get IoU above 0.5, and our lesion area barely tracks the
   real one (Pearson r 0.08). Virus classes are worst (IoU 0.03 to 0.04) because they show as
   yellowing and curling, not spots. It also gives non zero values on healthy leaves (shadows
   and pale parts), so it is only run for disease labels. The bands (mild, moderate, severe)
   should be read as a hint, not a measurement.

3. **Potato early blight is strong on one source only.** Field F1 is 0.964 over 172 photos,
   but 158 of them are PLD single-leaf crops from Punjab (155 right). On the 14 web photos the
   model gets 8 right, mostly confusing it with late blight on busy photos with many leaves
   (see `gradcam/`).

4. **The photo quality gate is only tested on made-up bad photos.** Thresholds were set
   from real test photos, but "bad" photos were simulated: darkened copies, Gaussian blurred
   copies and greyscale copies standing in for "no leaf" (`quality_gate.md`). We have no real
   photos of soil, hands or sky, and green backgrounds such as grass will pass as leaf.

5. **MobileNetV3-Small does not survive INT8.** The same post training quantization that
   costs Large 2.6 points of field macro F1 drops Small from 0.834 to 0.201
   (`small_vs_large.md`). We did not try quantization aware training, so Small is not an
   option for now and we ship Large INT8.

6. **Laptop timings are not phone timings.** All latency numbers in these docs are from a
   laptop CPU. Phone numbers come from the app side.

7. **Leaves of other plants often get an answer.** On 325 PlantVillage leaves of 14 other crops,
   the full rule (quality gate, crop mass >= 0.8, top probability >= 0.56) still gives a
   confident tomato or potato diagnosis in 20 percent of cases (29 percent when the farmer picks
   tomato, 11 percent potato). The quality gate catches almost none of them. Non-plant photos
   were not tested. See `ood_and_threshold.md`.

8. **Works on leaf close-ups, not whole plants.** The model sees only the centre square of
   the photo (shorter side to 256, centre crop 224) and gives one label per photo. If the
   sick leaf is small or off centre, it mostly sees soil, sky or healthy leaves, and busy
   photos with many leaves are where it already goes wrong (potato early blight against late
   blight, see `gradcam/`). Severity is the share of one leaf that is diseased, so it also
   assumes one leaf. It cannot say where on the plant the disease is or report two problems
   in one photo. The app asks for a photo filled with the sick leaf. Next step: a leaf or
   lesion detector (YOLO style, trained on the PlantDoc and PlantSeg boxes and masks) that
   finds the sick leaves in a whole-plant photo and classifies each one.
