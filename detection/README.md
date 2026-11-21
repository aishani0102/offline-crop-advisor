# Detection

Photo of a leaf plus the crop name in, one JSON object out (see `docs/INTERFACE.md`).
A MobileNetV3 classifier picks the condition and a plain OpenCV step estimates severity.

All data and model files live outside the repo. On the laptop we use:

```
<data_root>/raw/<source>/   downloads, one folder per source
<data_root>/built/          resized images + manifest.csv
<data_root>/models/<run>/   best.pt, temperature.json, .pte files, logs
```

Run everything from the repo root. `-I` keeps Python from picking up stray files
from the current folder, which matters because the downloads are not our code.

## Setup

```
python -m venv <data_root>/venv
<data_root>/venv/Scripts/activate
pip install -r detection/requirements.txt
```

## 1. Download

```
python -I detection/data/download.py --root <data_root>
```

About 1.5 GB in total. It only fetches tomato and potato folders from the GitHub
sources (sparse, partial clones) and the two classes we use from the Indonesia set.
Running it again skips what is done, and the PlantSeg zip resumes.
PlantDoc has file names with `?` in them, so we write those files out with `_` instead.

## 2. Build the dataset

```
python -I detection/data/build_dataset.py --root <data_root>
```

Takes about 3 minutes. It hashes every image, removes near-duplicates across all
sources, makes the splits and balances train, saves each image once with the shorter
side at 256 px, and writes `built/manifest.csv` and `docs/data_counts.md`.
The split fingerprint in `docs/data_counts.md` changes if the splits change.

## 3. Train

```
python -I detection/train.py --root <data_root> --out <data_root>/models/mnv3_large --arch large --epochs 15 --frozen-epochs 3
```

Options that matter: `--device cpu|cuda|auto`, `--batch-size`, `--num-workers`,
`--epochs` (total), `--frozen-epochs` (head only), `--limit N` (tiny smoke test),
`--no-amp`, `--resume <best.pt>` (load those weights and run only stage 2, for more
fine tuning of a model we already have; arch and size come from the checkpoint).
Mixed precision is on by default on CUDA.

Writes `best.pt` (best validation macro F1), `temperature.json`, `train_log.txt`
(seconds per step and per epoch) and `train_summary.json` (total time and history).

Quick check that the pipeline runs (a few minutes on the laptop):

```
python -I detection/train.py --root <data_root> --out <data_root>/models/smoke --limit 300 --epochs 2 --frozen-epochs 1
```

## Training on Colab

`detection/train_colab.ipynb` trains on a free T4 GPU. Open it in Colab from GitHub,
set `BRANCH` in the first cell, pick Runtime > T4 GPU, and run all cells. It clones
the repo, downloads and builds the dataset (cached on Drive as one zip, so a reconnect
does not download again), trains with mixed precision, evaluates, and copies
`best.pt`, `temperature.json`, the logs and the metrics to
`MyDrive/offline-crop-advisor/runs/<timestamp>_mnv3_<arch>/`.

The build uses the same seed as the laptop. Check that the split fingerprint printed
in the notebook matches `docs/data_counts.md`. Then copy `best.pt` and
`temperature.json` into `<data_root>/models/mnv3_large/` and run
evaluate and export below on the laptop.

## 4. Evaluate

```
python -I detection/evaluate.py --root <data_root> --ckpt <data_root>/models/mnv3_large/best.pt --tag mnv3_large_fp32_pytorch
```

Writes `docs/results/<tag>/metrics.md`, `metrics.json` and a confusion matrix per set.
The lab test set is PlantVillage only. The field test set has field photos only and is
the number that matters. "Crop known" accuracy only lets the model choose between
classes of the true crop, because the app asks for the crop first.

## 5. Export to ExecuTorch

```
python -I detection/export.py --root <data_root> --ckpt <data_root>/models/mnv3_large/best.pt
```

Writes `mnv3_large_fp32.pte`, `mnv3_large_int8.pte` and `mnv3_large_meta.json` next to
the checkpoint. INT8 is PT2E post-training quantization with the XNNPACK quantizer,
calibrated on 160 field and 96 lab training images. It then re-scores both files
through the ExecuTorch Python runtime and saves size and latency to
`docs/results/export_mnv3_large.json`. The latency is batch 1 on this x86 laptop
(i5-1135G7, 4 threads), not on a phone.

## 6. Severity

```
python -I detection/severity.py --image leaf.jpg --save-mask mask.png
python -I detection/severity.py --eval-plantseg --root <data_root>
```

Lesion pixels divided by leaf pixels, from HSV colour rules. The second command
compares our lesion mask with the PlantSeg lesion masks (IoU and Dice) and writes
`docs/results/severity/`. Bands come from `configs/thresholds.json`.
If no leaf is found, `severity_pct` is `null` and `severity_band` is `"no_leaf"`.

## 7. Predict

```
python -I detection/predict.py --image leaf.jpg --crop tomato --model <data_root>/models/mnv3_large/best.pt
python -I detection/predict.py --image leaf.jpg --crop tomato --model <data_root>/models/mnv3_large/mnv3_large_int8.pte
```

Prints the JSON from `docs/INTERFACE.md`. Only classes of the given crop are
considered, confidence is after temperature scaling, and `uncertain` is true below
the threshold in `configs/thresholds.json`.
