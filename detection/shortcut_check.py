"""Look for signs that the model learned the source of a photo instead of the disease.

    python -I detection/shortcut_check.py --root <data_root> --tag mnv3_large_fp32_pytorch

Uses the saved predictions from evaluate.py (docs/results/<tag>/preds_*.npz), so it
does not run the model again. Prints markdown tables to paste into shortcut_check.md.
"""
import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import REPO, load_classes, read_manifest  # noqa: E402


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return "\n".join(out + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--tag", default="mnv3_large_fp32_pytorch")
    args = ap.parse_args()
    classes = load_classes()
    labels = [c["label"] for c in classes]
    crop_of = np.array([c["crop"] for c in classes])
    rows = {r["image"]: r for r in read_manifest(Path(args.root) / "built" / "manifest.csv")}
    res = REPO / "docs" / "results" / args.tag

    def load(split):
        d = np.load(res / f"preds_{split}.npz")
        logits, y, imgs = d["logits"], d["y"], d["images"]
        pred = logits.argmax(1)
        masked = np.where(crop_of[None, :] == crop_of[y][:, None], logits, -np.inf)
        return y, pred, masked.argmax(1), [rows[i]["source"] for i in imgs]

    y, pred, pred_crop, src = load("test_field")

    print("## Field test accuracy per source\n")
    out = []
    for s in sorted(set(src)):
        idx = np.array([x == s for x in src])
        out.append([s, int(idx.sum()), f"{(pred[idx] == y[idx]).mean():.3f}",
                    f"{(pred_crop[idx] == y[idx]).mean():.3f}"])
    print(table(["source", "images", "accuracy", "crop known accuracy"], out))

    print("\n## Field test per class and source (correct / images, plain argmax)\n")
    cell = defaultdict(lambda: [0, 0])
    for t, p, s in zip(y, pred, src):
        cell[(t, s)][0] += int(t == p)
        cell[(t, s)][1] += 1
    srcs = sorted(set(src))
    out = [[labels[c]] + [f"{cell[(c, s)][0]}/{cell[(c, s)][1]}" if cell[(c, s)][1] else "" for s in srcs]
           for c in sorted(set(y.tolist()))]
    print(table(["class"] + srcs, out))

    print("\n## Field test, potato rows of the confusion matrix (plain argmax)\n")
    pot = [i for i, c in enumerate(classes) if c["crop"] == "potato"]
    out = []
    for t in pot:
        cnt = Counter(pred[y == t].tolist())
        other = sum(v for k, v in cnt.items() if k not in pot)
        out.append([labels[t]] + [cnt.get(p, 0) for p in pot] + [other])
    print(table(["true \\ predicted"] + [labels[p] for p in pot] + ["any tomato class"], out))

    print("\n## What field photos from each source get called (plain argmax)\n")
    for s in srcs:
        idx = [i for i, x in enumerate(src) if x == s]
        cnt = Counter(labels[pred[i]] for i in idx)
        print(f"- {s} ({len(idx)}): " + ", ".join(f"{k} {v}" for k, v in cnt.most_common()))

    yl, pl, plc, _ = load("test_lab")
    print("\n## Lab test (PlantVillage), potato classes\n")
    out = []
    for t in pot:
        cnt = Counter(labels[p] for p in pl[yl == t])
        out.append([labels[t], int((yl == t).sum()), ", ".join(f"{k} {v}" for k, v in cnt.most_common())])
    print(table(["true class", "images", "predicted as"], out))

    lm = labels.index("tomato_leaf_miner")
    tv_idx = [i for i, s in enumerate(src) if s == "tomato_village"]
    not_lm = [i for i in tv_idx if y[i] != lm]
    called_lm = [i for i in not_lm if pred[i] == lm]
    other_src_called_lm = [i for i, s in enumerate(src) if s != "tomato_village" and pred[i] == lm]
    print("\n## Leaf miner\n")
    print(f"- Tomato-Village field test images that are not leaf miner: {len(not_lm)}, "
          f"predicted as leaf miner: {len(called_lm)}")
    print(f"- Field test images from other sources predicted as leaf miner: {len(other_src_called_lm)}")
    acc_tv_other = np.mean([pred[i] == y[i] for i in not_lm])
    print(f"- Accuracy on the other Tomato-Village classes: {acc_tv_other:.3f}")


if __name__ == "__main__":
    main()
