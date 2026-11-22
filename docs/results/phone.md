# Phone results

Phone: Redmi 12 5G (Snapdragon 4 Gen 2, arm64-v8a, Android 15, about 1.8 to 2.3 GB free RAM).
Runtime: executorch-android 1.5.1 from Maven, the same version the .pte files were exported with.
All numbers come from `timings.log`, which the app writes to its files folder
(`/sdcard/Android/data/app.cropadvisor/files/timings.log`). Raw logs from 21 Nov 2026 are kept
with the model files, outside the repo.

## Leaf model (mnv3_large_int8.pte, 4.5 MB, bundled in the APK)

| What | Value |
|---|---|
| Classify one photo (resize, crop, forward pass) | 70 to 300 ms, first run after start is the slowest |
| Phone vs PC on the same test images | top 3 matched (checkpoint B); test_015492.jpg gives Septoria leaf spot at 0.885 on the phone |
| Fresh install, nothing pushed | classifies, model loaded from the APK assets |

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

Hindi (same image, severe Septoria leaf spot, grounded Hindi prompt, seq_len 1024): load 3.6 s,
time to first token 19.3 s, 84 tokens, 27.6 s in total, peak RSS 1517 MB, passed the safety check.
Hindi gets seq_len 1024 (the full context of the exported model) because Hindi needs about 3 times
the tokens of English and in the PC eval 12 of 13 fallbacks hit the 200 new token limit. English
keeps 768. The Hindi prompt is long, so most of the wait is prefill.

## Severity (Severity.kt from the detection branch)

| What | Value |
|---|---|
| Golden file, 8 field photos, phone vs `severity.py` | 8 of 8 within 1 point (all identical to 0.1, same band) |
| Time per photo, old Severity.kt (sevtest) | 2613 ms first photo, then 113 to 266 ms |
| Time per photo, faster Severity.kt (sevtest, 22 Nov) | 2148 ms first photo, then 12 to 42 ms; still 8 of 8 |
| Time in the app flow, faster version | 570 to 836 ms (test_015492.jpg, 74.2%, severe) |

Severity only runs for disease and pest labels; a healthy leaf scores 26% with this colour method.
A `no_leaf` result counts as uncertain, like `check_case` in the advisory code, so no treatment is
named. Spray advice comes back only for moderate and severe, as in `knowledge.py`.

## Free RAM gate

The app only starts Llama when the phone reports at least **1900 MB** free (`Advisor.LLAMA_NEEDS_MB`).
The advisory code on the PC uses 2544 MB (2032 MB peak measured on the laptop plus 512 MB margin).
On the phone the whole app peaked at 1559 MB with Llama loaded, so 1900 MB leaves about 340 MB
margin. With the old 2544 MB gate Llama never ran on this phone (free RAM was 2117 to 2274 MB).
Below the gate the app shows the template advice, which uses the same KB facts.

## Differences from the Python advisory code

- **KVK line retry.** If the Llama answer fails the safety check only because the KVK or Kisan
  Call Centre line is missing, the app adds the fixed KB referral sentence and checks again. In the
  first phone run Llama dropped that line and the answer fell back to the template; with the retry
  the same answer passed. The Python code (`advisory/safety.py`) does not do this retry.
- **Languages.** The app offers English, Hindi, Bengali, Marathi, Tamil and Telugu. Llama only
  writes English and Hindi. Bengali, Marathi, Tamil and Telugu always get the translated template
  from `assets/kb_<lang>.json`. Those files are marked `"reviewed": false` and only hold the text
  the phone template shows now; anything missing falls back to English. Hindi comes from `kb.json`,
  where `hindi_reviewed` is still false. The photo hint ("Fill the photo with the sick leaf, in daylight") in Hindi,
  Bengali, Marathi, Tamil and Telugu has not been reviewed by a native speaker yet.

## Healthy potato check (22 Nov 2026)

20 healthy potato test photos (8 Indonesia full-size 1500x1500, 8 Ethiopia, 4 PlantVillage) were run
through the app's real photo path with `--ez visiontest true --es crop potato`. The phone gave 20/20
potato_healthy (confidence 0.967 to 0.999), the same as the PC INT8 model (20/20, 0.962 to 0.999).

So the app pipeline is not why healthy potatoes are called late blight on real phone photos. The
cause is the training data: the only healthy potato field photos come from Indonesia and Ethiopia.
The PLD dataset (Punjab, Pakistan) was added on the `detection` branch and a retrain is pending.

Top matches are now hidden when a photo fails the quality gate (too dark, too blurry, no leaf);
see `app_screens/invalid_photo_no_matches.png`. Low-confidence (< 0.6) results on good photos still
show them. The app also has its own launcher icon (`app_screens/launcher_icon.png`).

## Photo resize: one step is now the default (22 Nov 2026)

Camera photos are now resized to the model input in one step (`Photo.stepShrink = false`). The old
step-by-step halving is still there for comparison with `--ez stepshrink true`. In the earlier
comparison on 5 large camera photos (big1-5.jpg), one-step matched the PC on 5 of 5 and
step-by-step on 4 of 5. The re-run on 22 Nov (visiontest, no crop filter) gave:

| Photo | Size | One step (default) | Step by step |
|---|---|---|---|
| big1 | 1424x1068 | potato_late_blight 0.984 | potato_late_blight 0.988 |
| big2 | 1072x1072 | tomato_healthy 0.519 | tomato_yellow_leaf_curl_virus 0.365 |
| big3 | 2000x1500 | tomato_early_blight 0.320 | tomato_early_blight 0.527 |
| big4 | 2000x1333 | tomato_septoria_leaf_spot 0.959 | tomato_septoria_leaf_spot 0.936 |
| big5 | 2000x1500 | tomato_late_blight 0.351 | potato_late_blight 0.435 |

The two methods disagree on the top-1 label for big2 and big5. The PC reference labels are not
stored in the repo, so this re-run was not scored against the PC again.

## Offline check (airplane mode, 22 Nov 2026)

Airplane mode on: `settings get global airplane_mode_on` = 1, no `NetworkAgentInfo` entries in
`dumpsys connectivity` ("Active default network: none"), and `ping 8.8.8.8` failed with
"Network is unreachable". The full flow (test_015492.jpg, tomato, answers yes,growing,no) ran
10 times in a row: classify `tomato_septoria_leaf_spot` 0.885, severity 74.2% severe, then
`advice mode=llm ... fails=[]` every time (load 2.6 to 4.1 s, first token 12.4 to 13.4 s,
total 18.2 to 19.4 s, 69 tokens, peak 1547 to 1620 MB). Screenshot with the airplane icon:
`app_screens/airplane_mode_flow.png`.

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
