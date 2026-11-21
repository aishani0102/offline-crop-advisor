"""Score a trained model on the lab test set and the field-only test set.

    python -I detection/evaluate.py --root <data_root> --ckpt <data_root>/models/mnv3l/best.pt --tag mnv3l_fp32_pytorch
    python -I detection/evaluate.py --root ... --pte <data_root>/models/mnv3l/mnv3l_int8.pte --tag mnv3l_int8_pte

Writes docs/results/<tag>/metrics.json, metrics.md and one confusion matrix
PNG per test set. "Crop known" accuracy only lets the model pick between the
classes of the true crop, because the app asks the farmer for the crop first.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import matplotlib
import numpy as np
import torch
from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import REPO, ManifestDataset, eval_transform, load_checkpoint, load_classes, read_manifest  # noqa: E402

SETS = {"test_lab": "Lab test (PlantVillage)", "test_field": "Field test (field photos only)"}


class TorchRunner:
    def __init__(self, ckpt, threads=4):
        torch.set_num_threads(threads)
        self.model, ck = load_checkpoint(ckpt)
        self.size = ck["size"]
        self.labels = ck["labels"]
        self.kind = "pytorch"

    def logits(self, x):
        with torch.no_grad():
            return self.model(x)


class PteRunner:
    """Runs an ExecuTorch .pte file one image at a time (it is exported with batch 1)."""

    def __init__(self, pte, size, labels):
        from executorch.runtime import Runtime
        self.method = Runtime.get().load_program(Path(pte)).load_method("forward")
        self.size = size
        self.labels = labels
        self.kind = "pte"

    def logits(self, x):
        outs = [self.method.execute([x[i:i + 1].contiguous()])[0] for i in range(len(x))]
        return torch.cat(outs)


def run_set(runner, rows, built, batch=32):
    ds = ManifestDataset(rows, built, eval_transform(runner.size))
    dl = torch.utils.data.DataLoader(ds, batch_size=batch, num_workers=0)
    out, ys = [], []
    t0 = time.time()
    for x, y in dl:
        out.append(runner.logits(x).float())
        ys.append(y)
    return torch.cat(out), torch.cat(ys), time.time() - t0


def metrics(logits, y, temperature, labels, classes):
    crop_of = np.array([{c["label"]: c["crop"] for c in classes}[lb] for lb in labels])
    probs = torch.softmax(logits / temperature, 1).numpy()
    y = y.numpy()
    pred = probs.argmax(1)
    present = sorted(set(y.tolist()))
    p, r, f, s = precision_recall_fscore_support(y, pred, labels=present, zero_division=0)
    # crop known: zero out the other crop before taking the top class
    masked = probs * (crop_of[None, :] == crop_of[y][:, None])
    pred_crop = masked.argmax(1)
    conf = probs.max(1)
    return {
        "n": int(len(y)),
        "accuracy": float((pred == y).mean()),
        "macro_f1": float(f1_score(y, pred, labels=present, average="macro", zero_division=0)),
        "crop_known_accuracy": float((pred_crop == y).mean()),
        "crop_known_macro_f1": float(f1_score(y, pred_crop, labels=present, average="macro", zero_division=0)),
        "crop_wrong_rate": float((crop_of[pred] != crop_of[y]).mean()),
        "mean_confidence": float(conf.mean()),
        "per_class": {labels[c]: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]),
                                  "support": int(s[i])} for i, c in enumerate(present)},
        "confusion": confusion_matrix(y, pred, labels=range(len(labels))).tolist(),
        "_pred": pred, "_y": y, "_conf": conf,
    }


def plot_confusion(cm, labels, title, path):
    cm = np.array(cm)
    keep = (cm.sum(1) > 0) | (cm.sum(0) > 0)
    cm = cm[keep][:, keep]
    names = [lb for lb, k in zip(labels, keep) if k]
    norm = cm / np.maximum(cm.sum(1, keepdims=True), 1)
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
    for i in range(len(names)):
        for j in range(len(names)):
            if cm[i, j]:
                ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=8,
                        color="white" if norm[i, j] > 0.5 else "black")
    ax.set_xticks(range(len(names)), names, rotation=60, ha="right", fontsize=8)
    ax.set_yticks(range(len(names)), names, fontsize=8)
    ax.set_xlabel("predicted")
    ax.set_ylabel("true")
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def write_report(results, out_dir, tag, model_desc):
    out_dir.mkdir(parents=True, exist_ok=True)
    clean = {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in results.items()}
    (out_dir / "metrics.json").write_text(json.dumps({"tag": tag, "model": model_desc, "sets": clean}, indent=1))
    lines = [f"# Results: {tag}", "", f"Model: {model_desc}", "",
             "| set | images | accuracy | macro F1 | crop known accuracy | crop known macro F1 | wrong crop |",
             "|---|---|---|---|---|---|---|"]
    for k, v in clean.items():
        lines.append(f"| {SETS[k]} | {v['n']} | {v['accuracy']:.4f} | {v['macro_f1']:.4f} | "
                     f"{v['crop_known_accuracy']:.4f} | {v['crop_known_macro_f1']:.4f} | {v['crop_wrong_rate']:.4f} |")
    for k, v in clean.items():
        lines += ["", f"## {SETS[k]}, per class", "", "| class | precision | recall | F1 | images |", "|---|---|---|---|---|"]
        for lb, m in v["per_class"].items():
            lines.append(f"| {lb} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {m['support']} |")
        lines += ["", f"![confusion {k}](confusion_{k}.png)"]
    (out_dir / "metrics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def evaluate(runner, root, temperature, tag, model_desc, sets=("test_lab", "test_field"), out_root=None):
    classes = load_classes()
    built = Path(root) / "built"
    rows = read_manifest(built / "manifest.csv")
    out_dir = Path(out_root or REPO / "docs" / "results") / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    for s in sets:
        sub = [r for r in rows if r["split"] == s]
        logits, y, secs = run_set(runner, sub, built)
        m = metrics(logits, y, temperature, runner.labels, classes)
        m["seconds"] = round(secs, 1)
        results[s] = m
        plot_confusion(m["confusion"], runner.labels, f"{tag}: {SETS[s]}", out_dir / f"confusion_{s}.png")
        print(f"{tag} {s}: n {m['n']} acc {m['accuracy']:.4f} macro F1 {m['macro_f1']:.4f} "
              f"crop known acc {m['crop_known_accuracy']:.4f} ({secs:.0f} s)")
        np.savez(out_dir / f"preds_{s}.npz", logits=logits.numpy(), y=y.numpy(),
                 images=np.array([r["image"] for r in sub]))
    write_report(results, out_dir, tag, model_desc)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--ckpt", required=True, help="best.pt (also used for labels and input size with --pte)")
    ap.add_argument("--pte", help="evaluate this .pte file instead of the PyTorch model")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--sets", nargs="*", default=["test_lab", "test_field"])
    ap.add_argument("--threads", type=int, default=4)
    args = ap.parse_args()
    torch.set_num_threads(args.threads)
    ck_dir = Path(args.ckpt).parent
    temperature = json.loads((ck_dir / "temperature.json").read_text())["temperature"]
    if args.pte:
        ck = torch.load(args.ckpt, map_location="cpu", weights_only=False)
        runner = PteRunner(args.pte, ck["size"], ck["labels"])
        desc = f"{Path(args.pte).name} through the ExecuTorch Python runtime, arch {ck['arch']}"
    else:
        runner = TorchRunner(args.ckpt, args.threads)
        ck = torch.load(args.ckpt, map_location="cpu", weights_only=False)
        desc = f"PyTorch FP32 checkpoint, MobileNetV3-{ck['arch']}, input {ck['size']}"
    evaluate(runner, args.root, temperature, args.tag, desc + f", temperature {temperature:.3f}", args.sets)


if __name__ == "__main__":
    main()
