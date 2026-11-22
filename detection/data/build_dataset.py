"""Build the train, validation and test splits from the raw downloads.

    python -I detection/data/build_dataset.py --root <data_root>

Reads <root>/raw, writes resized copies and manifest.csv to <root>/built, and
writes docs/data_counts.md in the repo. The plan it follows is docs/DATASETS.md.

Steps:
1. Collect every image we want and map it to one of our 10 classes.
2. Perceptual hash each image and save a resized copy (shorter side 256).
3. Group near-duplicates across all sources. A group whose images disagree
   on the class is dropped. Otherwise one image is kept, and if any copy is in
   a test split, the test copy is the one we keep.
4. Assign splits, then balance train (field first up to 700, lab fill to 1,000).
"""
import argparse
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

import imagehash
import numpy as np
from PIL import Image, ImageOps

REPO = Path(__file__).resolve().parents[2]
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

FIELD_CAP = 700
CLASS_TARGET = 1000
LAB_VAL_CAP = 100      # lab val per class, so validation is not mostly lab photos
LAB_TEST_CAP = 200     # lab test per class
HASH_DIST = 4          # phash bits (out of 64) that still count as the same photo
SEED = 0

PLANTVILLAGE = {
    "Potato___Early_blight": "potato_early_blight",
    "Potato___Late_blight": "potato_late_blight",
    "Potato___healthy": "potato_healthy",
    "Tomato___Early_blight": "tomato_early_blight",
    "Tomato___Late_blight": "tomato_late_blight",
    "Tomato___Leaf_Mold": "tomato_leaf_mold",
    "Tomato___Septoria_leaf_spot": "tomato_septoria_leaf_spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "tomato_yellow_leaf_curl_virus",
    "Tomato___healthy": "tomato_healthy",
}
PLANTDOC = {
    "Potato leaf early blight": "potato_early_blight",
    "Potato leaf late blight": "potato_late_blight",
    "Tomato Early blight leaf": "tomato_early_blight",
    "Tomato Septoria leaf spot": "tomato_septoria_leaf_spot",
    "Tomato leaf late blight": "tomato_late_blight",
    "Tomato leaf yellow virus": "tomato_yellow_leaf_curl_virus",
    "Tomato leaf": "tomato_healthy",
    "Tomato mold leaf": "tomato_leaf_mold",
}
PLANTSEG = {
    "potato early blight": "potato_early_blight",
    "potato late blight": "potato_late_blight",
    "tomato early blight": "tomato_early_blight",
    "tomato late blight": "tomato_late_blight",
    "tomato leaf mold": "tomato_leaf_mold",
    "tomato septoria leaf spot": "tomato_septoria_leaf_spot",
    "tomato yellow leaf curl virus": "tomato_yellow_leaf_curl_virus",
}
TOMATO_VILLAGE = {
    "Early_blight": "tomato_early_blight",
    "Healthy": "tomato_healthy",
    "Late_blight": "tomato_late_blight",
    "Leaf Miner": "tomato_leaf_miner",
}
INDONESIA = {"Phytophthora": "potato_late_blight", "Healthy": "potato_healthy"}
ETHIOPIA = {"Healthy": "potato_healthy", "Late Blight": "potato_late_blight"}
# PLD, Central Punjab, Pakistan (Kaggle rizwan123456789/potato-disease-leaf-datasetpld)
PLD = {"Early_Blight": "potato_early_blight", "Healthy": "potato_healthy", "Late_Blight": "potato_late_blight"}
PLD_SPLITS = {"Training": "train", "Validation": "val", "Testing": "test"}

SPLIT_NAMES = {"train": "train", "training": "train", "val": "val", "validation": "val", "test": "test"}


def images_in(folder):
    # sort by the plain file name so Windows and Linux give the same order (and the same splits)
    return sorted((p for p in Path(folder).iterdir() if p.suffix.lower() in IMG_EXT), key=lambda p: p.name)


def collect(raw):
    """Return one dict per image: path, source, domain, label, src_split, mask."""
    recs = []

    def add(path, source, domain, label, src_split="", mask=""):
        recs.append(dict(orig_path=str(path), source=source, domain=domain, label=label,
                         src_split=src_split, mask_path=str(mask) if mask else ""))

    pv = raw / "plantvillage" / "raw" / "color"
    for d, label in PLANTVILLAGE.items():
        for p in images_in(pv / d):
            add(p, "plantvillage", "lab", label)

    pd_root = raw / "plantdoc" / "files"
    for split in ("train", "test"):
        for d, label in PLANTDOC.items():
            for p in images_in(pd_root / split / d):
                add(p, "plantdoc", "field", label, split)

    ps = raw / "plantseg" / "extracted" / "plantseg"
    with open(ps / "Metadata.csv", newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            label = PLANTSEG.get(row["Disease"].strip().lower())
            if label is None:
                continue
            split = SPLIT_NAMES[row["Split"].strip().lower()]
            img = ps / "images" / split / row["Name"]
            mask = ps / "annotations" / split / row["Label file"]
            if img.exists():
                add(img, "plantseg", "field", label, split, mask if mask.exists() else "")

    tv = raw / "tomato_village" / "Variant-a(Multiclass Classification)"
    for split in ("train", "val", "test"):
        for d, label in TOMATO_VILLAGE.items():
            for p in images_in(tv / split / d):
                add(p, "tomato_village", "field", label, split)

    for d, label in INDONESIA.items():
        for p in images_in(raw / "potato_indonesia" / d):
            add(p, "potato_indonesia", "field", label)

    eth = raw / "potato_ethiopia" / "extracted" / "Local"
    for d, label in ETHIOPIA.items():
        for p in images_in(eth / d):
            add(p, "potato_ethiopia", "field", label)

    # added last so the image numbers of the older sources do not change
    pld = raw / "pld" / "extracted" / "PLD_3_Classes_256"
    for sd, split in PLD_SPLITS.items():
        for d, label in PLD.items():
            for p in images_in(pld / sd / d):
                add(p, "pld", "field", label, split)
    return recs


def hash_and_resize(args):
    """Worker: open once, hash, save the 256 px copy. Returns (hash, w, h) or None."""
    src, dst = args
    try:
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            w, h = im.size
            ph = int(str(imagehash.phash(im)), 16)
            s = 256 / min(w, h)
            if s < 1:
                im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.BILINEAR)
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            im.save(dst, "JPEG", quality=92)
        return ph, w, h
    except Exception as e:
        print(f"  skip unreadable {src}: {e}")
        return None


def near_duplicate_groups(hashes, max_dist):
    """Union-find over all pairs with hamming distance <= max_dist."""
    h = np.array(hashes, dtype=np.uint64)
    parent = list(range(len(h)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    step = 512
    for start in range(0, len(h), step):
        block = h[start:start + step]
        d = np.bitwise_count(block[:, None] ^ h[None, :])
        ii, jj = np.nonzero(d <= max_dist)
        for i, j in zip(ii + start, jj):
            if j > i:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[rj] = ri
    groups = defaultdict(list)
    for i in range(len(h)):
        groups[find(i)].append(i)
    return list(groups.values())


def keep_priority(r):
    # test copies win (so the train copy is the one removed), then field over lab
    return (r["src_split"] != "test", r["domain"] != "field")


def take(items, n, rng):
    items = list(items)
    rng.shuffle(items)
    return items[:n], items[n:]


def assign_splits(recs, rng):
    by = defaultdict(list)
    for r in recs:
        by[(r["source"], r["label"])].append(r)
    for (source, label), items in sorted(by.items()):
        if source == "pld":
            # published split, no random draw, so the other sources get the same splits as before
            for r in items:
                r["split"] = r["src_split"] if r["src_split"] in ("test", "val") else "pool"
        elif source in ("plantdoc", "plantseg", "tomato_village"):
            # use the split the authors published; PlantDoc has no val, so 10 percent of its train
            rest = []
            for r in items:
                if r["src_split"] in ("test", "val"):
                    r["split"] = r["src_split"]
                else:
                    rest.append(r)
            if source == "plantdoc":
                val, rest = take(rest, round(0.1 * len(rest)), rng)
                for r in val:
                    r["split"] = "val"
            for r in rest:
                r["split"] = "pool"
        elif source in ("potato_indonesia", "potato_ethiopia"):
            test, rest = take(items, round(0.2 * len(items)), rng)
            val, rest = take(rest, round(0.1 * len(items)), rng)
            for r in test:
                r["split"] = "test"
            for r in val:
                r["split"] = "val"
            for r in rest:
                r["split"] = "pool"
        else:  # plantvillage
            n = len(items)
            test, rest = take(items, min(round(0.1 * n), LAB_TEST_CAP), rng)
            val, rest = take(rest, min(round(0.1 * n), LAB_VAL_CAP), rng)
            for r in test:
                r["split"] = "test_lab"
            for r in val:
                r["split"] = "val"
            for r in rest:
                r["split"] = "pool"
    # the field test set gets its own name so nobody mixes it up with lab test
    for r in recs:
        if r["split"] == "test":
            r["split"] = "test_field"

    # balance the train pool per class: field first, then lab to fill
    pool = defaultdict(lambda: {"field": [], "lab": [], "pld": []})
    for r in recs:
        if r["split"] == "pool":
            pool[r["label"]]["pld" if r["source"] == "pld" else r["domain"]].append(r)
    # PLD draws from its own generator, so the older sources keep the same draws
    pld_rng = random.Random(SEED + 1)
    for label, d in pool.items():
        field, extra_f = take(d["field"], FIELD_CAP, rng)
        lab, extra_l = take(d["lab"], max(0, CLASS_TARGET - len(field)), rng)
        # PLD fills the field cap, then replaces lab photos (from the end) to stay at the target
        pld, extra_p = take(d["pld"], max(0, FIELD_CAP - len(field)), pld_rng)
        over = max(0, len(field) + len(lab) + len(pld) - CLASS_TARGET)
        if over:
            lab, extra_l = lab[:len(lab) - over], lab[len(lab) - over:] + extra_l
        for r in field + lab + pld:
            r["split"] = "train"
        for r in extra_f + extra_l + extra_p:
            r["split"] = "unused"


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def write_counts(path, kept, stats, labels):
    splits = ["train", "val", "test_field", "test_lab", "unused"]
    sources = ["plantvillage", "plantdoc", "plantseg", "tomato_village", "potato_indonesia", "potato_ethiopia", "pld"]
    c_split = Counter((r["label"], r["split"]) for r in kept)
    rows = []
    for lb in labels:
        rows.append([lb] + [c_split[(lb, s)] for s in splits])
    rows.append(["total"] + [sum(c_split[(lb, s)] for lb in labels) for s in splits])

    lines = ["# Data counts", "",
             "Written by `detection/data/build_dataset.py`. These are the real counts after "
             "de-duplication and balancing. Plan and reasons are in `docs/DATASETS.md`.", "",
             "## Cleaning", ""]
    lines += [f"- {k}: {v}" for k, v in stats.items()]
    lines += ["", "## Images per class and split", "",
              "`unused` is what balancing left out of train (over the 700 field or 1,000 total cap).", "",
              md_table(["class"] + splits, rows), ""]
    for s in ["train", "val", "test_field", "test_lab"]:
        c = Counter((r["label"], r["source"]) for r in kept if r["split"] == s)
        used = [src for src in sources if any(c[(lb, src)] for lb in labels)]
        rows = [[lb] + [c[(lb, src)] for src in used] + [sum(c[(lb, src)] for src in used)] for lb in labels]
        lines += [f"## {s} by source", "", md_table(["class"] + used + ["total"], rows), ""]
    c = Counter((r["label"], r["domain"]) for r in kept if r["split"] == "train")
    rows = [[lb, c[(lb, "field")], c[(lb, "lab")]] for lb in labels]
    lines += ["## train field vs lab", "", md_table(["class", "field", "lab"], rows), ""]
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--counts", default=str(REPO / "docs" / "data_counts.md"))
    args = ap.parse_args()
    root = Path(args.root)
    built = root / "built"
    classes = json.loads((REPO / "configs" / "classes.json").read_text())["classes"]
    label_to = {c["label"]: c for c in classes}
    labels = [c["label"] for c in classes]
    rng = random.Random(SEED)

    recs = collect(root / "raw")
    print(f"collected {len(recs)} images")
    for i, r in enumerate(recs):
        r["image"] = f"images/{r['source']}/{i:06d}.jpg"
    jobs = [(r["orig_path"], str(built / r["image"])) for r in recs]
    with Pool(args.workers) as pool:
        results = pool.map(hash_and_resize, jobs, chunksize=32)
    ok = []
    for r, res in zip(recs, results):
        if res is not None:
            r["phash"], r["width"], r["height"] = res
            ok.append(r)
    stats = {"images found": len(recs), "unreadable, skipped": len(recs) - len(ok)}

    # PLD was added later and holds copies of older photos (PlantVillage among them).
    # Older sources are grouped on their own so their splits stay as before; a PLD
    # photo close to any older photo is dropped, the rest of PLD is grouped by itself.
    old = [r for r in ok if r["source"] != "pld"]
    new = [r for r in ok if r["source"] == "pld"]
    old_h = np.array([r["phash"] for r in old], dtype=np.uint64)
    removed_from = Counter()
    fresh = []
    for r in new:
        if (np.bitwise_count(old_h ^ np.uint64(r["phash"])) <= HASH_DIST).any():
            removed_from["pld"] += 1
        else:
            fresh.append(r)
    ok = old + fresh
    groups = near_duplicate_groups([r["phash"] for r in old], HASH_DIST)
    groups += [[len(old) + i for i in g] for g in near_duplicate_groups([r["phash"] for r in fresh], HASH_DIST)]
    kept, dup_removed, conflict_removed, cross_source = [], removed_from["pld"], 0, 0
    conflict_from = Counter()
    for g in groups:
        members = [ok[i] for i in g]
        if len({m["label"] for m in members}) > 1:
            conflict_removed += len(members)
            for m in members:
                m["split"] = "dropped_conflict"
                conflict_from[m["source"]] += 1
            continue
        if len({m["source"] for m in members}) > 1:
            cross_source += 1
        members.sort(key=keep_priority)
        kept.append(members[0])
        dup_removed += len(members) - 1
        for m in members[1:]:
            removed_from[m["source"]] += 1
    stats[f"near-duplicates removed (phash distance <= {HASH_DIST})"] = dup_removed
    stats["duplicate groups that span two or more sources"] = cross_source
    stats["images dropped because copies had different labels"] = conflict_removed
    stats["duplicates removed, by source"] = dict(sorted(removed_from.items()))
    stats["label-conflict images dropped, by source"] = dict(sorted(conflict_from.items()))
    stats["images found, by source"] = dict(sorted(Counter(r["source"] for r in recs).items()))
    stats["images left after cleaning"] = len(kept)

    assign_splits(kept, rng)

    # drop resized copies we will never use, to save disk
    kept_files = {r["image"] for r in kept if r["split"] != "unused"}
    for r in recs:
        if r["image"] not in kept_files:
            (built / r["image"]).unlink(missing_ok=True)

    fields = ["image", "orig_path", "source", "domain", "label", "label_id", "crop",
              "src_split", "split", "phash", "width", "height", "mask_path"]
    with open(built / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in sorted(kept, key=lambda r: r["image"]):
            if r["split"] == "unused":
                continue
            r["label_id"] = label_to[r["label"]]["id"]
            r["crop"] = label_to[r["label"]]["crop"]
            r["phash"] = f"{r['phash']:016x}"
            w.writerow({k: r.get(k, "") for k in fields})
    # a fingerprint of which original file went to which split, to check that two
    # builds (say laptop and Colab) made the same splits
    keyed = sorted(f"{r['source']}/{Path(r['orig_path']).parent.name}/{Path(r['orig_path']).name}:{r['split']}"
                   for r in kept if r["split"] != "unused")
    stats["split fingerprint (sha256, first 16)"] = hashlib.sha256("\n".join(keyed).encode()).hexdigest()[:16]
    write_counts(args.counts, kept, stats, labels)
    print(json.dumps(stats, indent=1))
    print(f"manifest: {built / 'manifest.csv'}")


if __name__ == "__main__":
    main()
