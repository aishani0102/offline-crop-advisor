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

## Accuracy

Small was trained on Colab (T4) with the optional cell at the end of
`detection/train_colab.ipynb`: batch 128, head lr 2e-3, full lr 4e-4, field weight 2, seed 0,
25 epochs, first 3 head only. It took 32.5 min, best epoch 23 (val macro F1 0.944), temperature
0.687. One difference: Large got its 25 epochs as a 15 epoch run and then 10 more epochs on
top, while Small ran 25 epochs in one schedule.

The INT8 .pte was made with `detection/export.py` exactly like Large (same 256 calibration
images, same quantizer), and both .pte files were re-scored through the ExecuTorch runtime
(`export_mnv3_small.json`, `mnv3_small_fp32_pte/`, `mnv3_small_int8_pte/`).

| model | field acc | field macro F1 | field crop known macro F1 | lab acc | INT8 field acc | INT8 field macro F1 | INT8 field macro F1 drop (points) | INT8 .pte | INT8 laptop ms |
|---|---|---|---|---|---|---|---|---|---|
| Large | 0.921 | 0.865 | 0.891 | 0.990 | 0.905 | 0.845 | 2.03 | 4.52 MB | 7.85 |
| Small | 0.891 | 0.834 | 0.877 | 0.989 | 0.300 | 0.201 | 63.33 | 1.73 MB | 5.51 |

Field and lab numbers are PyTorch FP32 with temperature scaling, 623 field and 1135 lab test
photos. Small FP32 as .pte gives the same numbers as PyTorch, so the export itself is fine.

What this shows:

- In FP32, Small is close on lab photos (0.989 vs 0.990) but about 3 points worse on field
  photos (macro F1 0.834 vs 0.865), which are the ones that matter for farmers.
- INT8 Small falls apart (field accuracy 0.30). The same post training quantization costs Large
  only 2 points. MobileNetV3-Small is known to be hard to quantize this way (small depthwise
  layers with wide value ranges); it would need quantization aware training or keeping some
  layers in FP32, which we have not tried.
- So the only usable Small is FP32: 6.15 MB and 6.5 ms, against Large INT8 at 4.52 MB and
  7.85 ms. Large INT8 is smaller, about as fast, and more accurate on field photos.

**Recommendation: keep Large (INT8).** Small INT8 is not usable, and Small FP32 is bigger than
Large INT8 while being about 3 points worse on field photos, for about 1 ms of speed.
