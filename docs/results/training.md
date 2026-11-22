# Training run used for Phase 1

The model we ship is MobileNetV3-Large (ImageNet weights), input 224, trained on a free
Colab T4 GPU with `detection/train_colab.ipynb`. The log and summary are in `training_logs/`.

## Run

- Command (from the notebook): `train.py --arch large --device cuda --batch-size 128 --num-workers 2 --epochs 25 --frozen-epochs 3`, mixed precision on.
- 9,421 train and 1,800 val images, split fingerprint `09129439436a1ece` (same as the laptop build, see `docs/data_counts.md`).
- Stage 1: 3 epochs with the backbone frozen, head lr 0.002. Stage 2: 22 epochs of full fine-tuning, lr 0.0004, one-cycle schedule. Field photos weighted 2x in the loss.
- Time: 83.0 s per epoch on average, 2,077 s in total (about 35 min) on a T4.
- Best epoch 24: val accuracy 0.9628, val macro F1 0.9630, field part of val macro F1 0.8920.
- Temperature fitted on val: 0.687 (val NLL 0.211 to 0.154).

## Laptop check

We re-ran `evaluate.py` on the laptop with the checkpoint (tag `mnv3_large_fp32_pytorch`). The numbers match the Colab evaluation exactly:

| set | images | accuracy | macro F1 | crop known accuracy | crop known macro F1 |
|---|---|---|---|---|---|
| Lab test (PlantVillage) | 1,135 | 0.9947 | 0.9951 | 0.9965 | 0.9968 |
| Field test | 1,020 | 0.9529 | 0.9191 | 0.9588 | 0.9226 |

Full per-class numbers are in `mnv3_large_fp32_pytorch/metrics.md`. Per source (PLD 0.992,
web sources 0.81) see `shortcut_check.md`.
