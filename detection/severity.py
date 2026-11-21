"""Baseline severity: lesion pixels divided by leaf pixels, with plain OpenCV.

    python -I detection/severity.py --image leaf.jpg
    python -I detection/severity.py --eval-plantseg --root <data_root>

How it works:
1. Healthy tissue is green in HSV (hue about 33 to 85 on OpenCV's 0 to 179 scale).
2. The leaf is the green area after closing small gaps and filling holes, so
   spots in the middle of a leaf count as leaf. Small blobs are dropped.
3. Lesion pixels are leaf pixels that are not healthy green (yellow, brown,
   black or grey patches).

This is a baseline. It cannot tell a leaf from green background, and lesions
at the very edge of a leaf that break the outline are missed. The Phase 2 plan
is a small U-Net or DeepLabV3 trained on PlantSeg lesion masks.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import REPO, load_thresholds  # noqa: E402

WORK_SIZE = 512


def _fill_holes(mask):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = np.zeros_like(mask)
    min_area = 0.01 * mask.size
    for c in contours:
        if cv2.contourArea(c) >= min_area:
            cv2.drawContours(out, [c], -1, 255, thickness=cv2.FILLED)
    return out


# tuned on the PlantSeg train split only (see tune_on_plantseg); test split is reported separately
# grid: h_lo 25/30/33/38, s_min 30/50/70, close_k 15/31 on 220 train images, mean IoU 0.13 to 0.17
PARAMS = {"h_lo": 38, "h_hi": 85, "s_min": 30, "v_min": 40, "close_k": 31}


def segment(bgr, params=None):
    """Return (leaf_mask, lesion_mask) as uint8 0/255 at the input resolution."""
    P = {**PARAMS, **(params or {})}
    h, w = bgr.shape[:2]
    s = WORK_SIZE / max(h, w)
    small = cv2.resize(bgr, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA) if s < 1 else bgr
    blur = cv2.GaussianBlur(small, (5, 5), 0)
    hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
    hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]

    healthy = ((hue >= P["h_lo"]) & (hue <= P["h_hi"]) & (sat >= P["s_min"])
               & (val >= P["v_min"])).astype(np.uint8) * 255
    # leafy colours in general, including yellowing and brown spots
    leafy = (((hue >= 10) & (hue <= 90) & (sat >= 40) & (val >= 30)) | (healthy > 0)).astype(np.uint8) * 255

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (P["close_k"], P["close_k"]))
    closed = cv2.morphologyEx(healthy, cv2.MORPH_CLOSE, k, iterations=2)
    leaf = _fill_holes(closed)
    # a leaf has to be mostly leaf coloured, so we do not fill in big patches of soil
    leaf = cv2.bitwise_and(leaf, cv2.dilate(leafy, k)) if leaf.any() else leaf
    leaf = cv2.morphologyEx(leaf, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))

    lesion = cv2.bitwise_and(leaf, cv2.bitwise_not(healthy))
    lesion = cv2.morphologyEx(lesion, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    if small is not bgr:
        leaf = cv2.resize(leaf, (w, h), interpolation=cv2.INTER_NEAREST)
        lesion = cv2.resize(lesion, (w, h), interpolation=cv2.INTER_NEAREST)
    return leaf, lesion


def band_for(pct, bands=None):
    bands = bands or load_thresholds()["severity_bands_pct"]
    for name, (lo, hi) in bands.items():
        if lo <= pct < hi or (hi >= 100 and pct >= lo):
            return name
    return "severe"


def severity(bgr):
    leaf, lesion = segment(bgr)
    leaf_px = int((leaf > 0).sum())
    if leaf_px == 0:
        return {"severity_pct": None, "severity_band": "no_leaf", "leaf_fraction": 0.0}
    pct = 100.0 * float((lesion > 0).sum()) / leaf_px
    return {"severity_pct": round(pct, 1), "severity_band": band_for(pct),
            "leaf_fraction": round(leaf_px / leaf.size, 3)}


def read_image(path):
    data = np.fromfile(str(path), dtype=np.uint8)  # works with non-ASCII Windows paths
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def eval_plantseg(root, out_dir):
    """IoU and Dice of our lesion mask against PlantSeg lesion masks."""
    ps = Path(root) / "raw" / "plantseg" / "extracted" / "plantseg"
    rows = []
    with open(ps / "Metadata.csv", newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["Plant"].strip().lower() in ("tomato", "potato"):
                rows.append(r)
    split_dir = {"training": "train", "validation": "val", "test": "test"}
    res = []
    for r in rows:
        sp = split_dir[r["Split"].strip().lower()]
        img = read_image(ps / "images" / sp / r["Name"])
        gt = cv2.imread(str(ps / "annotations" / sp / r["Label file"]), cv2.IMREAD_GRAYSCALE)
        if img is None or gt is None:
            continue
        if gt.shape != img.shape[:2]:
            gt = cv2.resize(gt, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
        gt = gt > 0
        leaf, lesion = segment(img)
        pred = lesion > 0
        inter, union = float((pred & gt).sum()), float((pred | gt).sum())
        tot = float(pred.sum() + gt.sum())
        res.append({"name": r["Name"], "disease": r["Disease"], "split": sp,
                    "iou": inter / union if union else 1.0, "dice": 2 * inter / tot if tot else 1.0,
                    "pred_lesion_frac_image": float(pred.mean()), "gt_lesion_frac_image": float(gt.mean()),
                    "pred_severity_pct": 100 * float(pred.sum()) / max(1.0, float((leaf > 0).sum()))})
    iou = np.array([x["iou"] for x in res])
    dice = np.array([x["dice"] for x in res])
    pf = np.array([x["pred_lesion_frac_image"] for x in res])
    gf = np.array([x["gt_lesion_frac_image"] for x in res])
    by_split = {}
    for sp in ("train", "val", "test"):
        sel = [x for x in res if x["split"] == sp]
        by_split[sp] = {"n": len(sel), "mean_iou": float(np.mean([x["iou"] for x in sel])),
                        "mean_dice": float(np.mean([x["dice"] for x in sel]))}
    by = {}
    for d in sorted({x["disease"] for x in res}):
        sel = [x for x in res if x["disease"] == d]
        by[d] = {"n": len(sel), "mean_iou": float(np.mean([x["iou"] for x in sel])),
                 "mean_dice": float(np.mean([x["dice"] for x in sel]))}
    summary = {
        "images": len(res),
        "mean_iou": float(iou.mean()), "median_iou": float(np.median(iou)),
        "mean_dice": float(dice.mean()), "median_dice": float(np.median(dice)),
        "share_iou_over_0_5": float((iou > 0.5).mean()),
        "pearson_lesion_area_pred_vs_gt": float(np.corrcoef(pf, gf)[0, 1]),
        "by_split": by_split,
        "by_disease": by,
        "note": "PlantSeg masks mark lesions only, so leaf area (and our severity percentage) cannot be "
                "checked directly. IoU and Dice compare lesion masks over the whole image. All tomato and "
                "potato disease images are used. The colour thresholds were picked on 220 PlantSeg train images, "
                "so the test split number is the clean one.",
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "severity_plantseg.json").write_text(json.dumps(summary, indent=1))
    with open(out_dir / "severity_plantseg_per_image.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(res[0]))
        w.writeheader()
        w.writerows(res)
    print(json.dumps(summary, indent=1))
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image")
    ap.add_argument("--save-mask", help="write a picture of leaf (green) and lesion (red) masks")
    ap.add_argument("--eval-plantseg", action="store_true")
    ap.add_argument("--root")
    args = ap.parse_args()
    if args.eval_plantseg:
        eval_plantseg(args.root, REPO / "docs" / "results" / "severity")
        return
    img = read_image(args.image)
    print(json.dumps(severity(img)))
    if args.save_mask:
        leaf, lesion = segment(img)
        vis = img.copy()
        vis[leaf > 0] = (0.6 * vis[leaf > 0] + 0.4 * np.array([0, 200, 0])).astype(np.uint8)
        vis[lesion > 0] = (0.4 * vis[lesion > 0] + 0.6 * np.array([0, 0, 255])).astype(np.uint8)
        cv2.imwrite(args.save_mask, vis)


if __name__ == "__main__":
    main()
