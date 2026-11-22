# Smoke test only, not real results

These files only show that the pipeline runs end to end on the laptop. Do not quote
these numbers in the report.

- Model: MobileNetV3-Large, trained on 300 random train images for 2 epochs (1 frozen, 1 full),
  validated on 300 random val images.
- Train: `python -I detection/train.py --root <data_root> --out <data_root>/models/smoke --limit 300 --epochs 2 --frozen-epochs 1`
- Evaluate: `python -I detection/evaluate.py --root <data_root> --ckpt <data_root>/models/smoke/best.pt --tag smoke_test --sets test_field`
- Export: `python -I detection/export.py --root <data_root> --ckpt <data_root>/models/smoke/best.pt --field-only --calib-field 32 --calib-lab 16`

What it shows on the field test set (623 images): PyTorch FP32, FP32 .pte and INT8 .pte
all run. The FP32 .pte gives the same logits as PyTorch on the check image (max difference 0.0).
FP32 .pte is 16.88 MB and INT8 .pte is 4.52 MB. Median batch 1 latency through the
ExecuTorch Python runtime on the x86 laptop (i5-1135G7) is 12.2 ms for FP32 and 9.7 ms for INT8.
That is laptop latency, not phone latency, and the laptop was short on free RAM at the time.
The model is far from trained (field macro F1 about 0.31), so the accuracy numbers mean nothing yet.
