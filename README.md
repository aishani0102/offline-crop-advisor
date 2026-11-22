# Offline Crop Advisor

An offline field assistant for tomato and potato farmers, built for **PS1 of the Bharat AI-SoC Challenge 2026-27**. The farmer picks the crop, takes a photo of a sick leaf and answers three short questions. The phone says what is wrong, how much of the leaf is affected and what to do next, in English, Hindi, Bengali, Marathi, Tamil or Telugu. Everything runs on an Arm Android phone, with no internet at any point.

**Download the app:** [CropAdvisor-v1.0-phase1.apk](https://github.com/aishani0102/offline-crop-advisor/releases/tag/v1.0-phase1) · **Technical report:** [docs/technical_report.md](docs/technical_report.md) (also [Word](docs/Technical_Report.docx)) · **Dataset study:** [docs/Dataset_Study.pdf](docs/Dataset_Study.pdf)

## Results at a glance

Measured on a Redmi 12 5G (Snapdragon 4 Gen 2, Android 15) with ExecuTorch 1.5.1.

| | |
|---|---|
| Leaf classifier | MobileNetV3-Large, INT8, 4.5 MB; 70 to 300 ms per photo on the phone |
| Accuracy on field photos it never saw | 93.2% (macro F1 0.893) on 1,020 photos from six sources in four countries |
| Advice model | Llama 3.2 1B Instruct, SpinQuant INT4 (1.1 GB), on the phone; about 12 tokens/s |
| Advice safety | 60 of 60 test cases shown to the farmer passed every check (no invented chemicals or doses) |
| Offline | 10 of 10 full runs, photo to Llama advice, in airplane mode |
| Memory | about 1.55 GB peak with Llama loaded |
| Energy (Android estimate, CPU only) | about 3.2 mAh per diagnosis |

## How it works

```
Photo
  -> Quality gate        too dark / too blurry / no leaf  -> ask for a retake
  -> Leaf classifier     MobileNetV3-Large INT8 (ExecuTorch, XNNPACK), chosen crop only
                         not this crop / confidence < 0.56 -> "not sure", refer to KVK
  -> Severity            share of the leaf with lesions -> mild / moderate / severe
  -> 3 questions         rain, crop stage, already sprayed (+ month, state)
  -> Knowledge base      doses, pre-harvest interval, referral (NIPHM / PPQS and TNAU guidance)
  -> Llama 3.2 1B        rewrites the facts in the farmer's language, on the phone
  -> Safety check        pass -> Llama text    fail -> knowledge base text
```

- Llama only rewrites verified facts. A rule-based check rejects any chemical, dose or number that is not in the knowledge base, any banned chemical, and answers that drop the KVK referral; the farmer then sees the knowledge base text instead.
- If the photo is unclear, does not look like the chosen crop, or the model is unsure, no disease or treatment is named and the farmer is pointed to the nearest KVK or the Kisan Call Centre (1800-180-1551).
- Llama writes English and Hindi. Bengali, Marathi, Tamil and Telugu use translated knowledge base text.

## Classes

Tomato: healthy, early blight, late blight, leaf mold, Septoria leaf spot, yellow leaf curl virus, leaf miner (pest).
Potato: healthy, early blight, late blight.

The list is in `configs/classes.json`; thresholds are in `configs/thresholds.json`. Both stages read them from there.

## Repo layout

```
app/          Android app (Kotlin, Jetpack Compose, ExecuTorch)
detection/    data download, dataset build, training, evaluation, ExecuTorch export, severity
advisory/     knowledge base, prompt builder, safety check, Llama export and evaluation
configs/      class list and thresholds shared by all stages
docs/         technical report, dataset study, dataset sources and all results
scripts/      helper scripts
```

## Getting started (Python)

Python 3.10. Each stage has its own requirements and README with the exact commands.

```
python -m venv venv
venv\Scripts\activate                 (Windows)    or    source venv/bin/activate
pip install -r detection/requirements.txt
pip install -r advisory/requirements.txt
```

- Detection: [detection/README.md](detection/README.md). Data is downloaded from the original sources by `detection/data/download.py` and built by `detection/data/build_dataset.py`; no images are stored in this repo. Training runs on Colab with `detection/train_colab.ipynb`.
- Advisory: [advisory/README.md](advisory/README.md). The Llama model is downloaded and checked by `advisory/export_llama.py` after you accept the Llama 3.2 licence on Hugging Face.

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

## Results and documents

| Document | What it covers |
|---|---|
| [docs/technical_report.md](docs/technical_report.md) | Full technical report |
| [docs/Dataset_Study.pdf](docs/Dataset_Study.pdf), [docs/DATASETS.md](docs/DATASETS.md) | Data sources, cleaning, balancing and splits |
| [docs/results/training.md](docs/results/training.md), [export.md](docs/results/export.md) | Training run, FP32 and INT8 results |
| [docs/results/shortcut_check.md](docs/results/shortcut_check.md) | Accuracy per data source |
| [docs/results/ood_and_threshold.md](docs/results/ood_and_threshold.md) | Confidence threshold and other-crop rejection |
| [docs/results/small_vs_large.md](docs/results/small_vs_large.md) | MobileNetV3-Small against Large |
| [docs/results/advisory_eval.md](docs/results/advisory_eval.md) | Advice safety and grounding evaluation |
| [docs/results/phone.md](docs/results/phone.md) | Phone timings, memory, offline check and battery |
| [docs/results/limits.md](docs/results/limits.md) | Known limitations |

## Licences

Our code is under the MIT licence (`LICENSE`). Llama 3.2 is under the Llama 3.2 Community License (`LICENSES/`); the model file is not in this repo. Every dataset and knowledge source, with its licence, is listed in [NOTICE.md](NOTICE.md).
