# Phone results

Phone: Redmi 12 5G (Snapdragon 4 Gen 2, arm64-v8a, Android 15, about 1.8 to 2.3 GB free RAM).
Runtime: executorch-android 1.5.1 from Maven, the same version the .pte files were exported with.
All numbers come from `timings.log`, which the app writes to its files folder
(`/sdcard/Android/data/app.cropadvisor/files/timings.log`). Raw logs are kept with the model files,
outside the repo.

## Leaf model (MobileNetV3-Large INT8, 4.5 MB, bundled in the APK)

| What | Value |
|---|---|
| Classify one photo (resize, crop, forward pass) | 9 to 230 ms, first run after start is the slowest |
| PLD photos (Punjab, Pakistan), phone vs PC | 12 of 12 match |
| Fresh install, nothing pushed | classifies, model loaded from the APK assets |
| App update | the bundled model is copied again whenever the APK changes, so an update always runs the model shipped in it |

Photos are resized to the model input in one step. `--ez stepshrink true` switches to a
step-by-step resize for comparison.

## When the app says "Not sure"

Temperature T = 0.687, p = softmax(logits / T) over all 10 classes. For the crop the farmer chose:

- crop mass = sum of p over that crop's classes
- top = highest p among that crop's classes, divided by the crop mass

The result is uncertain if the photo fails the quality gate (too dark, too blurry, no leaf), or the
crop mass is below 0.80 (reason `not_crop`), or top is below 0.56 (reason `low_confidence`). The
values come from `configs/thresholds.json` on the detection branch. For quality failures and
`not_crop` the app shows "Not sure" with the reason and hides Top matches; for `low_confidence`
it still shows them. The classify log line includes `mass`.

Phone check, 22 Nov 2026 (visiontest, `--es crop`):

| Photo | Crop tomato: label, top, mass | Crop potato: label, top, mass |
|---|---|---|
| test_015467.jpg | leaf_mold 0.181, 0.010 | late_blight 0.987, 0.990 |
| test_015476.jpg | late_blight 0.827, 0.321 | late_blight 0.977, 0.679 |
| test_015483.jpg | leaf_mold 0.440, 0.857 | early_blight 0.728, 0.143 |
| test_015492.jpg | septoria_leaf_spot 0.543, 0.926 | late_blight 0.625, 0.074 |

test_015492.jpg (a tomato leaf) with crop potato gives mass 0.074, so `not_crop`:
`app_screens/not_crop.png`. With crop tomato it gives Septoria leaf spot at 0.543, just under 0.56,
so it is `low_confidence` and no treatment advice is given.

Top matches are also hidden for photos that fail the quality gate:
`app_screens/invalid_photo_no_matches.png`. Launcher icon: `app_screens/launcher_icon.png`.

## Language model (Llama 3.2 1B Instruct SpinQuant INT4, 1.1 GB, pushed with adb)

| What | Short test prompt (40 tokens) | Grounded advice prompt (KB facts) |
|---|---|---|
| Load | 2.4 to 5.1 s | 5.7 to 7.4 s |
| Time to first token | 1.3 to 1.9 s | 7.9 to 8.0 s |
| Decode speed | 9.8 to 14.2 tokens/s | about 12 tokens/s (95 tokens in 8.0 s) |
| Peak RSS of the app | 1559 MB | 1511 to 1538 MB |

Why time to first token is so different: prefill runs at about 30 tokens/s on this phone. The
short test prompt is 40 tokens, so it takes about 1.3 s. The grounded prompt carries the system
rules plus the KB facts for the case (about 230 tokens), so prefill alone takes about 7.5 s.

Hindi (severe Septoria leaf spot, grounded Hindi prompt, seq_len 1024): load 3.6 s,
time to first token 19.3 s, 84 tokens, 27.6 s in total, peak RSS 1517 MB, passed the safety check.
Hindi gets seq_len 1024 (the full context of the exported model) because Hindi needs about 3 times
the tokens of English and in the PC eval 12 of 13 fallbacks hit the 200 new token limit. English
keeps 768. The Hindi prompt is long, so most of the wait is prefill.

## Severity (Severity.kt from the detection branch)

| What | Value |
|---|---|
| Golden file, 8 field photos, phone vs `severity.py` | 8 of 8 within 1 point (all identical to 0.1, same band) |
| Time per photo (sevtest) | about 2.1 s for the first photo, then 12 to 42 ms |
| Time in the app flow | 130 to 1760 ms (74.2%, severe) |

Severity only runs for disease and pest labels; a healthy leaf scores 26% with this colour method.
A `no_leaf` result counts as uncertain, like `check_case` in the advisory code, so no treatment is
named. Spray advice comes back only for moderate and severe, as in `knowledge.py`.

## Free RAM gate

The app only starts Llama when the phone reports at least **1900 MB** free (`Advisor.LLAMA_NEEDS_MB`).
The advisory code on the PC uses 2544 MB (2032 MB peak measured on the laptop plus 512 MB margin).
On the phone the whole app peaked at 1559 MB with Llama loaded, so 1900 MB leaves about 340 MB
margin. A 2544 MB gate would never let Llama run on this phone (free RAM was 2117 to 2274 MB).
Below the gate the app shows the template advice, which uses the same KB facts.

## Differences from the Python advisory code

- **KVK line retry.** If the Llama answer fails the safety check only because the KVK or Kisan
  Call Centre line is missing, the app adds the fixed KB referral sentence and checks again. The
  Python code (`advisory/safety.py`) does not do this retry.
- **Languages.** The app offers English, Hindi, Bengali, Marathi, Tamil and Telugu. Llama only
  writes English and Hindi. Bengali, Marathi, Tamil and Telugu always get the translated template
  from `assets/kb_<lang>.json`. Those files are marked `"reviewed": false` and only hold the text
  the phone template shows now; anything missing falls back to English. Hindi comes from `kb.json`,
  where `hindi_reviewed` is still false. The photo hint ("Fill the photo with the sick leaf, in
  daylight") and the `not_crop` message in Hindi, Bengali, Marathi, Tamil and Telugu have not been
  reviewed by a native speaker yet.

## Offline check (airplane mode, 22 Nov 2026)

Airplane mode on: `settings get global airplane_mode_on` = 1, no `NetworkAgentInfo` entries in
`dumpsys connectivity` ("Active default network: none"), and `ping 8.8.8.8` failed with
"Network is unreachable". The full flow (classify, severity 74.2% severe, answers
yes,growing,no, Llama advice) ran 10 times in a row with `advice mode=llm ... fails=[]` every time
(load 2.6 to 4.1 s, first token 12.4 to 13.4 s, total 18.2 to 19.4 s, 69 tokens, peak 1547 to
1620 MB). Screenshot with the airplane icon: `app_screens/airplane_mode_flow.png`.

## Battery (software estimate, 22 Nov 2026)

This is Android's `batterystats` estimate, not a meter. The phone was on USB with
`dumpsys battery unplug` and `batterystats --reset`, in airplane mode, running the 10 flows above
(about 4.4 minutes). `dumpsys battery reset` was run afterwards.

| What | Value |
|---|---|
| App estimated use, 10 diagnoses with Llama advice | 32.1 mAh (CPU only, about 4 min 46 s of CPU time) |
| Per diagnosis | about 3.2 mAh |
| Battery capacity (batterystats learned; design is 5000 mAh) | 4381 mAh |
| Diagnoses per full charge, app CPU only | about 1360 |
| Battery level before / after | 100% / 100% (full battery, so no visible drop) |

The estimate covers the app's CPU only. The screen is not counted, so real use per diagnosis is
higher. `charge_full_design` was not readable (permission denied).
