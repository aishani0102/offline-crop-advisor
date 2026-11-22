# ExecuTorch export of the Phase 1 model

Command: `python -I detection/export.py --root <data_root> --ckpt <data_root>/models/mnv3_large_pld/best.pt --name mnv3_large`
(writes `mnv3_large_fp32.pte`, `mnv3_large_int8.pte` and `mnv3_large_meta.json` next to the checkpoint)

Both files use the XNNPACK delegate. INT8 is PT2E post-training quantization with the XNNPACK
quantizer (symmetric, per-channel weights), calibrated on 160 field and 96 lab training images.
All numbers below come from running the .pte files through the ExecuTorch Python runtime
(details in `export_mnv3_large.json`, per class in `mnv3_large_fp32_pte/` and `mnv3_large_int8_pte/`).

| model | size | lab macro F1 | field accuracy | field macro F1 | field crop known accuracy | median latency, x86 laptop |
|---|---|---|---|---|---|---|
| PyTorch FP32 (reference) | 17.0 MB checkpoint | 0.9951 | 0.9529 | 0.9191 | 0.9588 | 37.4 ms (eager) |
| FP32 .pte | 16.88 MB | 0.9951 | 0.9529 | 0.9191 | 0.9588 | 12.9 ms |
| INT8 .pte | 4.52 MB | 0.9860 | 0.9324 | 0.8928 | 0.9422 | 9.6 ms |

The FP32 .pte gives exactly the same predictions as PyTorch. INT8 loses 2.64 points of field
macro F1 and 0.91 points of lab macro F1. That is under the 3 point line we set, so post-training
quantization is good enough for Phase 1. Quantization-aware training is still worth trying in
Phase 2 to win those points back. Field test: 1,020 photos (397 of them PLD); per source see `shortcut_check.md`.

Latency is batch 1 at 224 x 224 on an Intel i5-1135G7 laptop CPU with 4 threads, 50 runs after
5 warm-up runs. **It is x86 laptop latency, not phone latency.** The phone number still has to be measured on the Arm device.
