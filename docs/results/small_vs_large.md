# MobileNetV3-Small vs Large

## Size and speed (measured now)

Small was built with ImageNet weights and our 10 class head (not trained yet; weights do not
change speed or file size). Both were exported with `detection/export.py` in the same way:
FP32 and INT8 ExecuTorch .pte with XNNPACK, INT8 calibrated on the same 256 images
(160 field + 96 lab train images, seed 0). Input 224x224, batch 1.

Latency: laptop CPU (Intel i5-1135G7), ExecuTorch Python runtime, 4 threads, 20 warmup runs
then 100 timed runs, repeated 3 times with the four files interleaved. The table shows the
median of the 3 medians, and the range of the 3 medians in brackets. This is not phone latency;
the app side will measure that on the phone.

| model | params | FP32 .pte | INT8 .pte | FP32 median ms | INT8 median ms | INT8 p90 ms |
|---|---|---|---|---|---|---|
| Large (mnv3_large_cont) | 4.2 M | 16.88 MB | 4.52 MB | 9.99 (9.07 to 10.23) | 7.85 (7.78 to 8.04) | 9.19 |
| Small (ImageNet weights) | 1.5 M | 6.15 MB | 1.73 MB | 6.54 (6.19 to 7.15) | 5.51 (5.32 to 6.63) | 6.50 |

So Small INT8 is about 2.6 times smaller than Large INT8 and about 30% faster on this laptop.
Both are already well under 50 ms here, so speed alone is not a strong reason to switch; the
choice depends on how much field accuracy Small loses.

## Accuracy (fill in after the Colab run)

Small is trained with the optional cell at the end of `detection/train_colab.ipynb`. The
settings match the Large run (batch 128, head lr 2e-3, full lr 4e-4, field weight 2, seed 0,
25 epochs, first 3 head only).
One difference: Large got its 25 epochs as a 15 epoch run and then 10 more epochs on top, while
Small runs 25 epochs in one schedule.

Then on the laptop, put `best.pt` and `temperature.json` in `<data_root>/models/mnv3_small/` and run
`python -I detection/export.py --root <data_root> --ckpt <data_root>/models/mnv3_small/best.pt --name mnv3_small`.

Field test set, 623 photos:

| model | field acc | field macro F1 | crop known macro F1 | INT8 field macro F1 drop (points) |
|---|---|---|---|---|
| Large | 0.921 | 0.865 | 0.891 | 2.03 |
| Small | TODO | TODO | TODO | TODO |

Large numbers are from `mnv3_large_cont` (PyTorch FP32, temperature scaled) and
`export_mnv3_large.json`.
