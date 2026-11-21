# ExecuTorch export of the Phase 1 model

Command: `python -I detection/export.py --root <data_root> --ckpt <data_root>/models/mnv3_large_cont/best.pt --name mnv3_large`

Both files use the XNNPACK delegate. INT8 is PT2E post-training quantization with the XNNPACK
quantizer (symmetric, per-channel weights), calibrated on 160 field and 96 lab training images.
All numbers below come from running the .pte files through the ExecuTorch Python runtime
(details in `export_mnv3_large.json`, per class in `mnv3_large_fp32_pte/` and `mnv3_large_int8_pte/`).

| model | size | lab macro F1 | field accuracy | field macro F1 | field crop known accuracy | median latency, x86 laptop |
|---|---|---|---|---|---|---|
| PyTorch FP32 (reference) | 17.0 MB checkpoint | 0.9911 | 0.9213 | 0.8651 | 0.9342 | 37.3 ms (eager) |
| FP32 .pte | 16.88 MB | 0.9911 | 0.9213 | 0.8651 | 0.9342 | 19.0 ms |
| INT8 .pte | 4.52 MB | 0.9862 | 0.9053 | 0.8448 | 0.9262 | 11.2 ms |

The FP32 .pte gives exactly the same predictions as PyTorch. INT8 loses 2.03 points of field
macro F1 and 0.49 points of lab macro F1. That is under the 3 point line we set, so post-training
quantization is good enough for Phase 1. Quantization-aware training is still worth trying in
Phase 2 to win those 2 points back.

Latency is batch 1 at 224 x 224 on an Intel i5-1135G7 laptop CPU with 4 threads, 50 runs after
5 warm-up runs. **It is x86 laptop latency, not phone latency.** The laptop was also short on free
RAM while this ran. The phone number still has to be measured on the Arm device.
