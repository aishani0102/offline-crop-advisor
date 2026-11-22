# Offline Crop Advisor

An offline field assistant for tomato and potato farmers. Take a photo of a sick leaf, and the phone tells you what is wrong, how bad it is, and what to do next, in English or Hindi. Nothing leaves the phone and it works in airplane mode.

Built for PS1 of the Bharat AI-SoC Challenge 2026-27. Target device is an Arm Android phone.

## How it works

The app runs two separate stages, one after the other, so only one model is in memory at a time.

1. **Detection.** A MobileNetV3 classifier (INT8, ExecuTorch with XNNPACK) looks at the photo and returns the crop, the condition and a confidence score. A severity estimate is worked out from how much of the leaf is covered in lesions.
2. **Advisory.** The result is turned into three short lines (crop, condition, severity) and passed to Llama 3.2 1B Instruct (4-bit, ExecuTorch with XNNPACK). Llama only rewrites verified advice from a local knowledge base built from ICAR and TNAU guidance. It never invents doses or chemical names.

If the model is unsure, or the case is severe, the app says so and points the farmer to the nearest KVK or the Kisan Call Centre (1800-180-1551).

## Classes

Tomato: healthy, early blight, late blight, leaf mold, Septoria leaf spot, yellow leaf curl virus, leaf miner (pest).
Potato: healthy, early blight, late blight.

The full list is in `configs/classes.json`, and both stages read it from there.

## Repo layout

```
configs/      class list shared by both stages
detection/    data download, dataset build, training, evaluation, ExecuTorch export
advisory/     knowledge base, prompt builder, Llama export and test runner
docs/         dataset sources, results and the technical report
scripts/      helper scripts
```

## Getting started

Python 3.10 is what we use.

```
python -m venv venv
venv\Scripts\activate          (Windows)    or    source venv/bin/activate
pip install -r requirements.txt
```

Each stage has its own README with the exact commands.

Model weights are not in the repo. The vision model is rebuilt with the training scripts, and the Llama model is downloaded and exported with `advisory/export_llama.py` after you accept the Llama 3.2 licence on Hugging Face.

## Run the app

Needs JDK 17 or newer (set `JAVA_HOME`) and the Android SDK. Put the SDK path in `app/local.properties`, e.g. `sdk.dir=C\:\\Users\\you\\AppData\\Local\\Android\\Sdk`.

```
cd app
gradlew :advisor:assembleDebug          (./gradlew on Linux/macOS)
adb install -r advisor/build/outputs/apk/debug/advisor-debug.apk
```

The leaf model is bundled in the APK. For Llama advice, push the exported model and tokenizer:

```
adb push llama.pte tokenizer.model /sdcard/Android/data/app.cropadvisor/files/
```

Without them the app shows the template advice.

Debug intent extras, for example `adb shell am start -S -n app.cropadvisor/.MainActivity --es classify test_015492.jpg --es crop tomato --es answers yes,growing,no`:

| Extra | What it does |
|---|---|
| `--es classify <file>` | Classify a photo from the files folder |
| `--es crop <name>` | Set the crop (tomato, potato, ...) |
| `--es answers a,b,c` | Pre-fill the follow-up questions (`-` skips one) |
| `--ez visiontest true` | Classify every `test_*.jpg` in the files folder and log the top 3 |
| `--ez sevtest true` | Check severity against `golden.json` and the golden photos |
| `--ez llmtest true` | Run the Llama test prompts |
| `--ez stepshrink true` | Use the old step-by-step photo resize (default is one step) |

Results go to logcat (tag `CropAdvisor`) and `timings.log` in the files folder.

## Datasets

See `docs/DATASETS.md` for every source, what we took from it, its licence and its link.
