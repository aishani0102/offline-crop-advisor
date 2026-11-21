# Known limits of the detection side

Short list of what the numbers do not show, for the report.

1. **Field accuracy is flattered by easy sources.** The shortcut check
   (`shortcut_check.md`) splits the field test set by source. On sets taken in one place with
   one camera (Tomato-Village, Indonesia, Ethiopia) accuracy is 97 to 100 percent. On the
   web-scraped sets (PlantDoc, PlantSeg), which are closer to random farmer photos, it is 74
   to 80 percent, about 0.78 overall. The headline field accuracy of 0.921 should always be
   shown next to this.

2. **Severity is a rough baseline.** It is a colour threshold method, not a trained
   segmenter. On PlantSeg test images the lesion mask has mean IoU 0.19 against the real
   masks, only 4 percent of images get IoU above 0.5, and our lesion area barely tracks the
   real one (Pearson r 0.08). Virus classes are worst (IoU 0.03 to 0.04) because they show as
   yellowing and curling, not spots. It also gives non zero values on healthy leaves (shadows
   and pale parts), so it is only run for disease labels. The bands (mild, moderate, severe)
   should be read as a hint, not a measurement.

3. **Potato early blight in the field is weak.** There are only 14 field test photos of it,
   and the model gets about 8 of them right (field F1 about 0.62), mostly confusing it with
   late blight on busy photos with many leaves (see `gradcam/`). With 14 photos this number
   is also very uncertain.

4. **The photo quality gate is only tested on made-up bad photos.** Thresholds were set
   from real test photos, but "bad" photos were simulated: darkened copies, Gaussian blurred
   copies and greyscale copies standing in for "no leaf" (`quality_gate.md`). We have no real
   photos of soil, hands or sky, and green backgrounds such as grass will pass as leaf.

5. **MobileNetV3-Small does not survive INT8.** The same post training quantization that
   costs Large 2 points of field macro F1 drops Small from 0.834 to 0.201
   (`small_vs_large.md`). We did not try quantization aware training, so Small is not an
   option for now and we ship Large INT8.

6. **Laptop timings are not phone timings.** All latency numbers in these docs are from a
   laptop CPU. Phone numbers come from the app side.
