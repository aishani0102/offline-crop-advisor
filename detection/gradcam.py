"""Grad-CAM pictures for a few field test photos, to see where the model looks.

    python -I detection/gradcam.py --root <data_root> --model <data_root>/models/mnv3_large_pld/best.pt --out docs/results/gradcam

Picks, for each class in --classes, one photo the model gets right and one it
gets wrong (first in manifest order), and saves photo | heat map side by side.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import MEAN, STD, eval_transform, load_checkpoint, read_manifest  # noqa: E402


def gradcam(model, x, target=None):
    """Grad-CAM on the last conv block. Returns (cam 0..1 at input size, predicted index)."""
    acts = {}
    layer = model.features[-1]
    h1 = layer.register_forward_hook(lambda m, i, o: acts.update(a=o))
    h2 = layer.register_full_backward_hook(lambda m, gi, go: acts.update(g=go[0]))
    logits = model(x)
    pred = int(logits.argmax(1))
    model.zero_grad()
    logits[0, pred if target is None else target].backward()
    h1.remove()
    h2.remove()
    w = acts["g"].mean((2, 3), keepdim=True)
    cam = torch.relu((w * acts["a"]).sum(1))[0]
    cam = cam / (cam.max() + 1e-8)
    cam = torch.nn.functional.interpolate(cam[None, None], size=x.shape[2:], mode="bilinear")[0, 0]
    return cam.detach().numpy(), pred


def overlay(x, cam):
    img = (x[0].permute(1, 2, 0).numpy() * np.array(STD) + np.array(MEAN)).clip(0, 1)
    heat = np.stack([cam, np.zeros_like(cam), 1 - cam], -1)  # red = high, blue = low
    mix = 0.55 * img + 0.45 * heat
    return (img * 255).astype(np.uint8), (mix * 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--classes", nargs="+",
                    default=["potato_early_blight", "tomato_healthy", "tomato_early_blight"])
    args = ap.parse_args()
    model, ck = load_checkpoint(args.model)
    labels, tf = ck["labels"], eval_transform(ck["size"])
    built = Path(args.root) / "built"
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = [r for r in read_manifest(built / "manifest.csv") if r["split"] == "test_field"]
    for cls in args.classes:
        want = {"right": None, "wrong": None}
        for r in rows:
            if r["label"] != cls or all(want.values()):
                continue
            with Image.open(built / r["image"]) as im:
                x = tf(im.convert("RGB"))[None]
            cam, pred = gradcam(model, x)
            kind = "right" if labels[pred] == cls else "wrong"
            if want[kind] is None:
                want[kind] = (r, x, cam, pred)
        for kind, hit in want.items():
            if hit is None:
                print(f"{cls}: no {kind} example")
                continue
            r, x, cam, pred = hit
            a, b = overlay(x, cam)
            pic = Image.new("RGB", (a.shape[1] * 2, a.shape[0] + 18), "white")
            pic.paste(Image.fromarray(a), (0, 18))
            pic.paste(Image.fromarray(b), (a.shape[1], 18))
            ImageDraw.Draw(pic).text((4, 3), f"true {cls}  pred {labels[pred]}", fill="black")
            name = f"{cls}_{kind}.png"
            pic.save(out / name, optimize=True)
            print(f"{name}: {r['image']} pred {labels[pred]}")


if __name__ == "__main__":
    main()
