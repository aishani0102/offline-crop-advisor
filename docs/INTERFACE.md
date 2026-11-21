# Detection to advisory interface

The detection stage and the advisory stage only talk through this one JSON object. Neither side should depend on anything else from the other.

```json
{
  "label": "tomato_early_blight",
  "crop": "tomato",
  "condition": "Early blight",
  "type": "disease",
  "confidence": 0.87,
  "top3": [
    {"label": "tomato_early_blight", "confidence": 0.87},
    {"label": "tomato_septoria_leaf_spot", "confidence": 0.08},
    {"label": "tomato_late_blight", "confidence": 0.03}
  ],
  "severity_pct": 18.5,
  "severity_band": "moderate",
  "uncertain": false,
  "language": "en"
}
```

## Fields

- `label`, `crop`, `condition`, `type`: copied from `configs/classes.json` for the top class.
- `confidence`: softmax probability of the top class, after temperature scaling.
- `top3`: the three most likely classes. Only classes for the crop the farmer picked are considered.
- `severity_pct`: percentage of leaf area covered by lesions, from 0 to 100. `null` for healthy leaves, and `null` when no leaf could be found in the photo.
- `severity_band`: `none` (healthy), `mild` (under 10), `moderate` (10 to 30), `severe` (over 30), `no_leaf` (the severity step found no leaf in the photo, so there is no severity estimate).
- `uncertain`: `true` when confidence is below the threshold set in `configs/thresholds.json`. The advisory stage must then avoid naming a treatment and should suggest a retake or a visit to the KVK.
- `language`: `en` or `hi`.

## Rules for the advisory side

- `no_leaf` means the disease label may still be fine, but the advisory side must not say how bad it is. Ask for a closer photo of one leaf.
- `severe` or `uncertain` always ends with a referral to the local KVK or the Kisan Call Centre (1800-180-1551).
- Chemical names and doses come only from the knowledge base entry for that label. Never from the model.
