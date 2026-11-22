"""Pick the "uncertain" threshold and test out-of-scope photos (other crops).

    python -I detection/ood_threshold.py --root <data_root> --model <data_root>/models/mnv3_large_pld/mnv3_large_int8.pte \
        --ood <data_root>/raw/plantvillage_ood

Runs the model the same way as predict.py (quality gate on the shorter-side-256 photo, then
10 logits) on the val split, the field test split and the out-of-scope photos listed in
<ood>/pick.txt, caches quality + logits in <data_root>/scores/, and prints markdown tables.
In-domain photos are scored with their true crop as the user's choice. Each out-of-scope photo
is scored twice, once as "tomato" and once as "potato".
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_classes, load_thresholds, read_manifest  # noqa: E402
from predict import Classifier, load_photo, photo_quality  # noqa: E402


def score(clf, paths, gate):
    q, lg = [], []
    for i, p in enumerate(paths):
        small, _ = load_photo(p)
        q.append(photo_quality(small, gate))
        lg.append(clf.logits(small).numpy())
        if i % 200 == 0:
            print(f"  {i}/{len(paths)}", file=sys.stderr)
    return np.array(q), np.stack(lg)


def cached(cache, clf, paths, gate):
    if cache.exists():
        d = np.load(cache)
        return d["quality"], d["logits"]
    q, lg = score(clf, paths, gate)
    np.savez(cache, quality=q, logits=lg, paths=np.array([str(p) for p in paths]))
    return q, lg


def softmax(z):
    z = z - z.max(1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(1, keepdims=True)


def features(logits, crop_idx, T, crop_of, labels):
    """Per row: crop-restricted top prob, its class, and the three 10-class OOD scores."""
    z = logits / T
    allowed = crop_of[None, :] == crop_idx[:, None]
    p10 = softmax(z)
    pr = softmax(np.where(allowed, z, -np.inf))
    m = z.max(1, keepdims=True)
    energy = -T * (m[:, 0] + np.log(np.exp(z - m).sum(1)))
    return {"top": pr.max(1), "pred": pr.argmax(1), "msp10": p10.max(1),
            "energy": energy, "mass": (p10 * allowed).sum(1)}


def auroc(pos, neg):
    """P(score of an in-domain photo > score of an out-of-scope photo)."""
    s = np.concatenate([pos, neg])
    r = s.argsort().argsort() + 1
    return (r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return "\n".join(out + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--ood", required=True)
    ap.add_argument("--threads", type=int, default=4)
    args = ap.parse_args()
    torch.set_num_threads(args.threads)
    root = Path(args.root)
    clf = Classifier(args.model)
    thr = load_thresholds()
    gate = thr["quality_gate"]
    classes = {c["label"]: c for c in load_classes()}
    labels = clf.labels
    crops = ["potato", "tomato"]
    crop_of = np.array([crops.index(classes[lb]["crop"]) for lb in labels])
    T = clf.temperature
    cache_dir = root / "scores"
    cache_dir.mkdir(exist_ok=True)
    tag = Path(args.model).stem

    rows = read_manifest(root / "built" / "manifest.csv")
    ind = {}
    for split in ("val", "test_field"):
        rs = [r for r in rows if r["split"] == split]
        q, lg = cached(cache_dir / f"{tag}_{split}.npz", clf, [root / "built" / r["image"] for r in rs], gate)
        y = np.array([labels.index(r["label"]) for r in rs])
        f = features(lg, crop_of[y], T, crop_of, labels)
        f.update(q=q, y=y, src=np.array([r["source"] for r in rs]), dom=np.array([r["domain"] for r in rs]))
        ind[split] = f
    ood_dir = Path(args.ood)
    picks = [ood_dir / ln.strip() for ln in (ood_dir / "pick.txt").read_text().splitlines() if ln.strip()]
    picks = [p for p in picks if p.exists()]
    q, lg = cached(cache_dir / f"{tag}_ood.npz", clf, picks, gate)
    n = len(picks)
    ood = features(np.concatenate([lg, lg]), np.repeat([crops.index("tomato"), crops.index("potato")], n),
                   T, crop_of, labels)
    ood["q"] = np.concatenate([q, q])
    ood["as"] = np.repeat(["tomato", "potato"], n)
    print(f"out-of-scope photos: {n} (x2 crop choices), temperature {T:.3f}\n")

    # 1. How well does each score separate in-domain (val, quality ok) from out-of-scope?
    v = ind["val"]
    okv, oko = v["q"] == "ok", ood["q"] == "ok"
    print("## Separation of val (quality ok) from out-of-scope (quality ok)\n")
    out = []
    for k, sign in (("top", 1), ("msp10", 1), ("mass", 1), ("energy", -1)):
        pos, neg = sign * v[k][okv], sign * ood[k][oko]
        keep95 = np.quantile(pos, 0.05)
        keep98 = np.quantile(pos, 0.02)
        out.append([k, f"{auroc(pos, neg):.3f}", f"{(neg >= keep95).mean():.3f}", f"{(neg >= keep98).mean():.3f}",
                    f"{sign * keep95:.3f}", f"{sign * keep98:.3f}"])
    print(table(["score", "AUROC", "OOD passed at 95% val kept", "OOD passed at 98% val kept",
                 "cutoff 95%", "cutoff 98%"], out))

    # 2. Out-of-scope outcome with the current app rule, per crop choice
    print("\n## Out-of-scope photos through the current rule (quality gate + crop-restricted top prob)\n")
    out = []
    for t in (0.5, 0.52, 0.6, 0.7, 0.8):
        for c in ("tomato", "potato"):
            s = ood["as"] == c
            gate_rej = (~oko & s).sum() / s.sum()
            conf_rej = (oko & s & (ood["top"] < t)).sum() / s.sum()
            out.append([t, c, f"{gate_rej:.3f}", f"{conf_rej:.3f}", f"{1 - gate_rej - conf_rej:.3f}"])
    print(table(["threshold", "crop chosen", "quality gate rejects", "confidence rejects", "confident diagnosis"], out))
    print("\nQuality gate reasons (each photo once): " + json.dumps(
        {k: int(c) for k, c in zip(*np.unique(q, return_counts=True))}))

    # 3. Grid: top prob threshold x crop-mass cutoff
    print("\n## Grid: val coverage / val answered accuracy / OOD answered\n")
    ts = (0.52, 0.56, 0.6, 0.64, 0.7)
    out = []
    for mc in (0.0, 0.5, 0.6, 0.7, 0.8, 0.9):
        cells = []
        for t in ts:
            a = okv & (v["top"] >= t) & (v["mass"] >= mc)
            ao = oko & (ood["top"] >= t) & (ood["mass"] >= mc)
            cells.append(f"{a.mean():.3f} / {(v['pred'][a] == v['y'][a]).mean():.4f} / {ao.mean():.3f}")
        out.append([f"{mc:.1f}"] + cells)
    print(table(["crop mass >="] + [f"top >= {t}" for t in ts], out))

    # 4. Threshold sweep, with and without the crop-mass rule
    mass_cut = thr.get("ood", {}).get("min_crop_mass")
    if mass_cut is None:
        mass_cut = float(np.floor(np.quantile(v["mass"][okv], 0.02) * 100) / 100)
    print(f"\ncrop-mass cutoff: {mass_cut:.2f}")

    def sweep(f, t, use_mass):
        ans = (f["q"] == "ok") & (f["top"] >= t)
        if use_mass:
            ans &= f["mass"] >= mass_cut
        return ans

    for use_mass in (False, True):
        for split in ("val", "test_field"):
            f = ind[split]
            name = f"{split}, " + ("with crop mass >= %.2f" % mass_cut if use_mass else "top prob only")
            print(f"\n## Sweep: {name}\n")
            out = []
            wrong = f["pred"] != f["y"]
            for t in np.round(np.arange(0.40, 0.801, 0.02), 2):
                a = sweep(f, t, use_mass)
                ao = sweep(ood, t, use_mass)
                out.append([f"{t:.2f}", f"{a.mean():.3f}", f"{(f['pred'][a] == f['y'][a]).mean():.4f}",
                            f"{(~a[wrong]).mean():.3f}", f"{ao.mean():.3f}",
                            f"{ao[ood['as'] == 'tomato'].mean():.3f}", f"{ao[ood['as'] == 'potato'].mean():.3f}"])
            print(table(["threshold", "coverage", "answered accuracy", "wrong caught",
                         "OOD answered", "OOD as tomato", "OOD as potato"], out))

    # 4. Field test per source at the chosen rule is printed for the doc
    t_sel = float(thr["uncertain_below_confidence"])
    f = ind["test_field"]
    a = sweep(f, t_sel, "ood" in thr)
    print(f"\n## Field test per source at threshold {t_sel} (ood rule {'on' if 'ood' in thr else 'off'})\n")
    out = []
    for s in sorted(set(f["src"])):
        i = f["src"] == s
        out.append([s, int(i.sum()), f"{a[i].mean():.3f}", f"{(f['pred'][i & a] == f['y'][i & a]).mean():.3f}"])
    print(table(["source", "images", "coverage", "answered accuracy"], out))


if __name__ == "__main__":
    main()
