# Severity on the phone

`detection/severity.py` is a colour threshold method (HSV masks, morphology, hole filling),
no model. `Severity.kt` is a plain Kotlin port of it with no OpenCV or other library, so it
can go straight into the app.

## Drop it in

1. Copy `Severity.kt` to `app/advisor/src/main/java/app/cropadvisor/` (package is
   `app.cropadvisor`).
2. Call it only when the classifier says a disease. For a healthy label keep
   `severity_band = "none"` and `severity_pct = null`, like `predict.py` does.

```kotlin
val r = Severity.estimate(bitmap)   // upright ARGB_8888 Bitmap, any size
// r.severityPct: Double? (null for no_leaf), r.band: mild / moderate / severe / no_leaf
```

The bitmap must be upright (apply the EXIF rotation first, as for the classifier) and
ARGB_8888. It is shrunk to 512 on the longer side inside. It takes about 100 ms per photo on
a laptop JVM, so run it off the main thread.

Settings at the top of the object, copied from `configs/thresholds.json`:
`mildBelowPct = 10`, `severeFromPct = 30`, `minLeafShare = 0.05`. If you load
thresholds.json in the app, set these from it.

`no_leaf` is returned when leaf coloured pixels are under `minLeafShare` (same rule as the
quality gate in `predict.py`) or when the leaf mask comes out empty. Then do not show a
severity, ask for a closer photo of one leaf (see docs/INTERFACE.md).

## Check against the golden file

`severity_golden.json` has 8 field test photos (8 different classes, one of them tomato_healthy)
with `severity_pct` and `severity_band` from `severity.py`. The photos are in
`<data_root>/built/<image>` on the team laptop. They are not in git (dataset images).

1. Copy the 8 jpgs into the app's `src/androidTest/assets/` locally (do not commit them).
2. In an instrumented test, decode each with `BitmapFactory` (`inPreferredConfig =
   ARGB_8888`, `inScaled = false`), call `Severity.estimate`, and check
   `abs(pct - golden) <= 1.0`.
3. The band should match too, except when the golden value is within 1 point of a band edge
   (10 or 30). `tomato_late_blight` is 10.0 in the file but `mild`, because the raw value is
   just under 10, so a small change there can flip it to `moderate`.

We checked the port on a desktop JVM by feeding it the same pixels OpenCV decoded: all 8
matched exactly (same pct to 0.1 and same band).

## Where Android can differ from Python

- **JPEG decoding.** `BitmapFactory` and OpenCV use different JPEG decoders, so a few pixel
  values can be off by 1 or 2. This is the most likely reason for small differences on the
  golden photos.
- **Resize.** Python shrinks with `cv2.INTER_AREA`; the port uses
  `Bitmap.createScaledBitmap(..., filter = true)` (bilinear). The golden photos are all
  under 512 so no resize happens there, but real camera photos will be shrunk and can differ a
  little.
- **Back to full size.** Python scales the masks back to the full photo before counting;
  the port counts on the 512 copy. It is a ratio, so the difference is tiny.
- **Hole filling.** Python drops shapes smaller than 1% of the photo using
  `cv2.contourArea`; the port uses the pixel count, which is a little bigger. Only shapes
  right at 1% can be kept in one and dropped in the other.
- **Blur and HSV.** These copy OpenCV's integer maths (5x5 kernel 1 4 6 4 1, reflect border,
  OpenCV's HSV tables with hue 0 to 179), so they should match exactly.
- **no_leaf gate.** `predict.py` checks leaf share on the 256 copy; the port checks it on the
  512 copy. Only photos right at 5% can differ.
- The healthy photo in the golden file gets 26.3 (moderate). That is the method seeing
  shadows and pale parts as lesions, and is why severity is skipped for healthy labels.
