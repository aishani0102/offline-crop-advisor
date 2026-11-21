"""Photo + crop name in, the detection JSON from docs/INTERFACE.md out.

    python -I detection/predict.py --image leaf.jpg --crop tomato --model <data_root>/models/mnv3_large/best.pt
    python -I detection/predict.py --image leaf.jpg --crop tomato --model <data_root>/models/mnv3_large/mnv3_large_int8.pte

For a .pte file the labels, input size and temperature come from
<name>_meta.json, which export.py writes next to it. For a .pt checkpoint
they come from the checkpoint and temperature.json in the same folder.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import eval_transform, load_checkpoint, load_classes, load_thresholds  # noqa: E402
from severity import severity  # noqa: E402


class Classifier:
    def __init__(self, model_path):
        p = Path(model_path)
        if p.suffix == ".pte":
            meta = json.loads(p.with_name(p.stem.rsplit("_", 1)[0] + "_meta.json").read_text())
            from executorch.runtime import Runtime
            method = Runtime.get().load_program(p).load_method("forward")
            self._run = lambda x: method.execute([x])[0]
            self.labels, self.size, self.temperature = meta["labels"], meta["size"], meta["temperature"]
        else:
            model, ck = load_checkpoint(p)
            self._run = lambda x: model(x)
            self.labels, self.size = ck["labels"], ck["size"]
            self.temperature = json.loads((p.parent / "temperature.json").read_text())["temperature"]
        self.tf = eval_transform(self.size)

    def logits(self, pil):
        x = self.tf(pil)[None]
        with torch.no_grad():
            return self._run(x)[0].float()


def load_photo(path):
    """Same preparation as the training copies: upright, RGB, shorter side 256."""
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
    full = im.copy()
    s = 256 / min(im.size)
    if s < 1:
        im = im.resize((round(im.size[0] * s), round(im.size[1] * s)), Image.BILINEAR)
    return im, full


def predict(clf, image_path, crop, language="en", classes=None, thresholds=None):
    classes = classes or load_classes()
    thresholds = thresholds or load_thresholds()
    info = {c["label"]: c for c in classes}
    small, full = load_photo(image_path)
    logits = clf.logits(small)
    allowed = torch.tensor([info[lb]["crop"] == crop for lb in clf.labels])
    if not allowed.any():
        raise ValueError(f"unknown crop {crop!r}")
    z = (logits / clf.temperature).masked_fill(~allowed, float("-inf"))
    probs = torch.softmax(z, 0)
    order = torch.argsort(probs, descending=True)
    top = [i for i in order.tolist() if allowed[i]][:3]
    best = clf.labels[top[0]]
    conf = float(probs[top[0]])
    c = info[best]

    if c["type"] == "healthy":
        sev_pct, band = None, "none"
    else:
        bgr = np.array(full)[:, :, ::-1].copy()
        sev = severity(bgr)
        sev_pct, band = sev["severity_pct"], sev["severity_band"]
    return {
        "label": best,
        "crop": c["crop"],
        "condition": c["condition"],
        "type": c["type"],
        "confidence": round(conf, 4),
        "top3": [{"label": clf.labels[i], "confidence": round(float(probs[i]), 4)} for i in top],
        "severity_pct": sev_pct,
        "severity_band": band,
        "uncertain": conf < thresholds["uncertain_below_confidence"],
        "language": language,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--crop", required=True, choices=["tomato", "potato"])
    ap.add_argument("--model", required=True, help="best.pt or a .pte file from export.py")
    ap.add_argument("--language", default="en", choices=["en", "hi"])
    ap.add_argument("--threads", type=int, default=4)
    args = ap.parse_args()
    torch.set_num_threads(args.threads)
    clf = Classifier(args.model)
    print(json.dumps(predict(clf, args.image, args.crop, args.language), indent=2))


if __name__ == "__main__":
    main()
