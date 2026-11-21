# Training run used for Phase 1

The model we ship is MobileNetV3-Large (ImageNet weights), input 224, trained on a free
Colab T4 GPU with `detection/train_colab.ipynb`. Logs are in `training_logs/`.

## Run 1: 15 epochs with train.py

- Command (from the notebook): `train.py --arch large --device cuda --batch-size 128 --num-workers 2 --epochs 15 --frozen-epochs 3`, mixed precision on.
- 9,011 train and 1,412 val images, split fingerprint `6d440b3fd40706b6` (same as the laptop build).
- Stage 1: 3 epochs with the backbone frozen, head lr 0.002. Stage 2: 12 epochs of full fine-tuning, lr 0.0004, one-cycle schedule.
- Time: 82.1 s per epoch on average (78.6 s of that is training, the rest is validation), 1,232.8 s in total (20.5 min).
- Best epoch 15, val macro F1 0.9520 (field part of val 0.8066). Val was still going up slowly, so we ran more epochs.
- Two copies of this run exist on Drive (`20261121_103648` and `20261121_103707`). Their `best.pt` files are byte-identical (same MD5), so they are the same run saved twice.

## Run 2: 10 more epochs from run 1

- Started from run 1's `best.pt` (the checkpoint stores `continued_from: .../20261121_103707_mnv3_large/best.pt`).
- 10 extra epochs, 76 to 86 s each, 800 s in total (13.3 min).
- Best at extra epoch 9 (epoch 24 overall): val macro F1 0.9566, field part of val 0.8235.
- Temperature fitted on val: 0.709 (val NLL 0.246 to 0.194).
- This continuation ran from a notebook cell written in Colab. The cell is not in the repo yet, so only its log is saved here (`training_logs/colab_continued_10_epochs_train_log.txt`). Its learning rate and schedule are not written in that log. To make the run repeatable, the simplest fix is to add a `--resume` option to `train.py`.

Total GPU training time for the shipped model: 1,232.8 + 800 = 2,032.8 s (about 34 min) on a T4.

## Laptop check

We re-ran `evaluate.py` on the laptop with the run 2 checkpoint (tag `mnv3_large_fp32_pytorch`). The numbers match the Colab evaluation exactly:

| set | images | accuracy | macro F1 | crop known accuracy | crop known macro F1 |
|---|---|---|---|---|---|
| Lab test (PlantVillage) | 1,135 | 0.9903 | 0.9911 | 0.9938 | 0.9945 |
| Field test | 623 | 0.9213 | 0.8651 | 0.9342 | 0.8907 |

Full per-class numbers are in `mnv3_large_fp32_pytorch/metrics.md`, and the Colab copy is in `mnv3_large_fp32_pytorch/colab_metrics.json`.
