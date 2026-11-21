"""Export the trained classifier to ExecuTorch .pte files (XNNPACK delegate).

    python -I detection/export.py --root <data_root> --ckpt <data_root>/models/mnv3l/best.pt

Writes <name>_fp32.pte and <name>_int8.pte next to the checkpoint. INT8 uses
PT2E post-training quantization with the XNNPACK quantizer (per-channel
symmetric weights), calibrated on a mix of lab and field training images.

Then it re-scores both .pte files through the ExecuTorch Python runtime on
the field test set (and the lab test set unless --field-only), and times one
image at a time. Timing is on this x86 laptop CPU, not on a phone.
"""
import argparse
import json
import os
import random
import statistics
import sys
import time
from pathlib import Path

import torch
from torch.export import export

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import REPO, ManifestDataset, eval_transform, load_checkpoint, read_manifest  # noqa: E402
from evaluate import PteRunner, evaluate  # noqa: E402


def _point_to_flatc():
    """On Windows the executorch wheel ships flatc.exe, but it only looks for
    'flatc' without the .exe, so tell it where the file is."""
    if os.environ.get("FLATC_EXECUTABLE"):
        return
    for cand in (Path(sys.executable).parent / "flatc.exe", Path(sys.executable).parent / "flatc"):
        if cand.is_file():
            os.environ["FLATC_EXECUTABLE"] = str(cand)
            return


def lower_to_pte(ep, path):
    _point_to_flatc()
    from executorch.backends.xnnpack.partition.xnnpack_partitioner import XnnpackPartitioner
    from executorch.exir import to_edge_transform_and_lower
    prog = to_edge_transform_and_lower(ep, partitioner=[XnnpackPartitioner()]).to_executorch()
    Path(path).write_bytes(prog.buffer)


def calibration_batches(root, size, n_field, n_lab, seed=0):
    built = Path(root) / "built"
    rows = [r for r in read_manifest(built / "manifest.csv") if r["split"] == "train"]
    rng = random.Random(seed)
    field = [r for r in rows if r["domain"] == "field"]
    lab = [r for r in rows if r["domain"] == "lab"]
    pick = rng.sample(field, min(n_field, len(field))) + rng.sample(lab, min(n_lab, len(lab)))
    rng.shuffle(pick)
    ds = ManifestDataset(pick, built, eval_transform(size))
    return torch.utils.data.DataLoader(ds, batch_size=16), len(pick)


def quantize_int8(model, example, calib):
    from executorch.backends.xnnpack.quantizer.xnnpack_quantizer import (
        XNNPACKQuantizer, get_symmetric_quantization_config)
    from torchao.quantization.pt2e.quantize_pt2e import convert_pt2e, prepare_pt2e
    q = XNNPACKQuantizer()
    q.set_global(get_symmetric_quantization_config(is_per_channel=True))
    # calibration runs in batches of 16, so export with a dynamic batch here
    batch = torch.export.Dim("batch", min=1, max=64)
    gm = export(model, (example.repeat(2, 1, 1, 1),), dynamic_shapes=({0: batch},)).module()
    gm = prepare_pt2e(gm, q)
    with torch.no_grad():
        for x, _ in calib:
            gm(x)
    gm = convert_pt2e(gm)
    return export(gm, (example,))


def time_pte(path, size, runs=50, warmup=5):
    from executorch.runtime import Runtime
    method = Runtime.get().load_program(Path(path)).load_method("forward")
    x = torch.randn(1, 3, size, size)
    for _ in range(warmup):
        method.execute([x])
    ts = []
    for _ in range(runs):
        t0 = time.perf_counter()
        method.execute([x])
        ts.append((time.perf_counter() - t0) * 1000)
    ts.sort()
    return {"median_ms": round(statistics.median(ts), 2), "p90_ms": round(ts[int(0.9 * len(ts)) - 1], 2),
            "mean_ms": round(statistics.mean(ts), 2), "runs": runs}


def time_torch(model, size, runs=50, warmup=5):
    x = torch.randn(1, 3, size, size)
    with torch.no_grad():
        for _ in range(warmup):
            model(x)
        ts = []
        for _ in range(runs):
            t0 = time.perf_counter()
            model(x)
            ts.append((time.perf_counter() - t0) * 1000)
    return {"median_ms": round(statistics.median(ts), 2), "mean_ms": round(statistics.mean(ts), 2), "runs": runs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--name", help="file name prefix, default is the checkpoint folder name")
    ap.add_argument("--calib-field", type=int, default=160)
    ap.add_argument("--calib-lab", type=int, default=96)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--field-only", action="store_true", help="only re-score the field test set")
    ap.add_argument("--skip-export", action="store_true", help="re-use existing .pte files")
    args = ap.parse_args()
    torch.set_num_threads(args.threads)

    ck_path = Path(args.ckpt)
    out_dir = ck_path.parent
    name = args.name or out_dir.name
    model, ck = load_checkpoint(ck_path)
    size = ck["size"]
    example = torch.randn(1, 3, size, size)
    temperature = json.loads((out_dir / "temperature.json").read_text())["temperature"]
    fp32_path, int8_path = out_dir / f"{name}_fp32.pte", out_dir / f"{name}_int8.pte"

    info = {"checkpoint": ck_path.name, "arch": ck["arch"], "input": size}
    # what predict.py (and the app) needs to use the .pte without the checkpoint
    (out_dir / f"{name}_meta.json").write_text(json.dumps(
        {"labels": ck["labels"], "size": size, "temperature": temperature, "arch": ck["arch"],
         "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225],
         "preprocess": "upright RGB, resize shorter side to 256, resize shorter side to "
                       f"{round(size * 256 / 224)}, center crop {size}, normalise"}, indent=1))
    if not args.skip_export:
        t0 = time.time()
        lower_to_pte(export(model, (example,)), fp32_path)
        print(f"fp32 export {time.time() - t0:.0f} s")
        calib, n_cal = calibration_batches(args.root, size, args.calib_field, args.calib_lab)
        t0 = time.time()
        lower_to_pte(quantize_int8(model, example, calib), int8_path)
        print(f"int8 export {time.time() - t0:.0f} s ({n_cal} calibration images)")
        info["calibration"] = {"field": args.calib_field, "lab": args.calib_lab}

    # check the .pte gives the same answer as PyTorch on one real image
    built = Path(args.root) / "built"
    row = next(r for r in read_manifest(built / "manifest.csv") if r["split"] == "test_field")
    x = ManifestDataset([row], built, eval_transform(size))[0][0][None]
    with torch.no_grad():
        ref = model(x)
    sets = ["test_field"] if args.field_only else ["test_lab", "test_field"]
    for kind, path in (("fp32", fp32_path), ("int8", int8_path)):
        runner = PteRunner(path, size, ck["labels"])
        diff = float((runner.logits(x) - ref).abs().max())
        res = evaluate(runner, args.root, temperature, f"{name}_{kind}_pte",
                       f"{path.name} (ExecuTorch {kind.upper()}, XNNPACK) through the Python runtime, "
                       f"temperature {temperature:.3f}", sets)
        info[kind] = {
            "file": path.name, "size_mb": round(path.stat().st_size / 1e6, 2),
            "max_abs_logit_diff_vs_pytorch_one_image": round(diff, 4),
            "latency_x86_laptop": time_pte(path, size),
            **{f"{s}_macro_f1": res[s]["macro_f1"] for s in sets},
            **{f"{s}_accuracy": res[s]["accuracy"] for s in sets},
            **{f"{s}_crop_known_accuracy": res[s]["crop_known_accuracy"] for s in sets},
        }
        print(kind, json.dumps(info[kind], indent=1))
    info["pytorch_eager_latency_x86_laptop"] = time_torch(model, size)
    info["note"] = ("Latency is batch 1 on an Intel i5-1135G7 laptop CPU with 4 threads through the "
                    "ExecuTorch Python runtime. It is not phone latency.")
    drop = info["fp32"]["test_field_macro_f1"] - info["int8"]["test_field_macro_f1"]
    info["int8_field_macro_f1_drop_points"] = round(100 * drop, 2)
    res_dir = REPO / "docs" / "results"
    (res_dir / f"export_{name}.json").write_text(json.dumps(info, indent=1))
    print(f"INT8 field macro F1 drop: {100 * drop:.2f} points")


if __name__ == "__main__":
    main()
