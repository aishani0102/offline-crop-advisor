"""Download only the parts of the six sources that we need.

Everything goes to <root>/raw/<source>/ outside the repo. Running it again
skips what is already there, and the big PlantSeg zip resumes where it
stopped.

    python -I detection/data/download.py --root <data_root>
    python -I detection/data/download.py --root ... --only plantdoc tomato_village

We never run anything that comes inside a download. Archives are only
extracted with tar (libarchive), which does not execute anything.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

UA = {"User-Agent": "crop-advisor-data-fetch/1.0"}

PLANTVILLAGE_DIRS = [
    "Potato___Early_blight", "Potato___Late_blight", "Potato___healthy",
    "Tomato___Early_blight", "Tomato___Late_blight", "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot", "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___healthy",
]
PLANTDOC_DIRS = [
    "Potato leaf early blight", "Potato leaf late blight", "Tomato Early blight leaf",
    "Tomato Septoria leaf spot", "Tomato leaf late blight", "Tomato leaf yellow virus",
    "Tomato leaf", "Tomato mold leaf",
]
TOMATO_VILLAGE_DIRS = ["Early_blight", "Healthy", "Late_blight", "Leaf Miner"]

PLANTSEG_URL = "https://zenodo.org/api/records/17719108/files/plantseg.zip/content"
PLANTSEG_MD5 = "9358a66dff88cdd15c4fe009763c40a3"
PLANTSEG_SIZE = 1057281724

MENDELEY_API = "https://data.mendeley.com/public-api/datasets/{id}"

# The Mendeley API lists files with a folder id but does not give the folder
# name. Each folder's file count matches exactly one class count in the paper
# (Shabrina et al. 2024: Phytophthora 347, Healthy 201, Fungi 748 and so on),
# so we pick folders by id. We only keep the two classes we use.
INDONESIA_FOLDERS = {
    "4893a56f-8b14-45df-ba31-921b9bcce728": "Phytophthora",
    "90fa4a30-0306-491c-875b-29958782e9f8": "Healthy",
}


def run(cmd, cwd=None):
    print(">", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def sparse_clone(url, dest, paths):
    """Partial clone that only fetches blobs for the folders we ask for."""
    if not (dest / ".git").exists():
        dest.mkdir(parents=True, exist_ok=True)
        run(["git", "-c", "core.longpaths=true", "clone", "--filter=blob:none",
             "--sparse", "--depth", "1", url, str(dest)])
    run(["git", "-c", "core.longpaths=true", "sparse-checkout", "set", "--cone", *paths], cwd=dest)
    # sparse-checkout set already checks out, this retries anything that failed half way
    run(["git", "-c", "core.longpaths=true", "checkout"], cwd=dest)


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def fetch(url, out, size=None, sha256=None, retries=5):
    """Download url to out, resuming a partial file with a Range request."""
    if out.exists() and size is not None and out.stat().st_size == size:
        return False
    out.parent.mkdir(parents=True, exist_ok=True)
    part = out.with_name(out.name + ".part")
    for attempt in range(retries):
        have = part.stat().st_size if part.exists() else 0
        headers = dict(UA)
        if have:
            headers["Range"] = f"bytes={have}-"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as r:
                mode = "ab" if have and r.status == 206 else "wb"
                with open(part, mode) as f:
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
            break
        except Exception as e:  # network hiccup, try again from where we are
            print(f"  retry {attempt + 1} for {out.name}: {e}")
            time.sleep(3 * (attempt + 1))
    else:
        raise RuntimeError(f"could not download {url}")
    if size is not None and part.stat().st_size != size:
        raise RuntimeError(f"{out.name}: got {part.stat().st_size} bytes, expected {size}")
    if sha256:
        h = hashlib.sha256(part.read_bytes()).hexdigest()
        if h != sha256:
            part.unlink()
            raise RuntimeError(f"{out.name}: sha256 mismatch")
    part.replace(out)
    return True


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def extract(archive, dest):
    """Extract an archive without running anything from it. Skips if done.

    Zip files use Python's zipfile (it strips absolute paths and '..').
    The Ethiopia rar needs bsdtar, which is the tar that ships with Windows,
    or unar/unrar on Linux."""
    marker = dest / ".extracted"
    if marker.exists():
        return
    dest.mkdir(parents=True, exist_ok=True)
    if archive.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive) as z:
            z.extractall(dest)
    elif sys.platform == "win32":
        run(["tar", "-xf", str(archive), "-C", str(dest)])
    elif shutil.which("bsdtar"):
        run(["bsdtar", "-xf", str(archive), "-C", str(dest)])
    elif shutil.which("unar"):
        run(["unar", "-q", "-o", str(dest), str(archive)])
    else:
        run(["unrar", "x", "-o+", str(archive), str(dest) + "/"])
    marker.write_text("ok\n")


def get_plantvillage(raw):
    sparse_clone("https://github.com/spMohanty/PlantVillage-Dataset.git",
                 raw / "plantvillage", [f"raw/color/{d}" for d in PLANTVILLAGE_DIRS])


def safe_name(name):
    for ch in '?*:"<>|':
        name = name.replace(ch, "_")
    return name.rstrip(" .")


def get_plantdoc(raw):
    """PlantDoc has file names with '?' in them (copied from web URLs), which
    Windows cannot check out. So we clone without a working tree, fetch the
    blobs for our folders with git backfill, and write them out ourselves with
    safe names."""
    dest = raw / "plantdoc"
    out_root = dest / "files"
    if (out_root / ".exported").exists():
        return
    if not (dest / ".git").exists():
        run(["git", "clone", "--filter=blob:none", "--no-checkout", "--depth", "1",
             "https://github.com/pratikkayal/PlantDoc-Dataset.git", str(dest)])
    lines = ["/*", "!/*/"]
    for split in ("train", "test"):
        lines += [f"/{split}/", f"!/{split}/*/"] + [f"/{split}/{d}/" for d in PLANTDOC_DIRS]
    (dest / ".git" / "info" / "sparse-checkout").write_text("\n".join(lines) + "\n")
    run(["git", "config", "core.sparseCheckout", "true"], cwd=dest)
    run(["git", "config", "core.sparseCheckoutCone", "true"], cwd=dest)
    try:
        run(["git", "backfill", "--sparse"], cwd=dest)
    except (subprocess.CalledProcessError, FileNotFoundError):
        # older git (Colab) has no backfill, but Linux can check out the odd names fine
        run(["git", "checkout"], cwd=dest)

    paths = [f"{split}/{d}/" for split in ("train", "test") for d in PLANTDOC_DIRS]
    ls = subprocess.run(["git", "ls-tree", "-r", "-z", "HEAD", "--", *paths], cwd=dest,
                        capture_output=True, check=True).stdout.decode("utf-8")
    entries = []
    for rec in ls.split("\0"):
        if not rec:
            continue
        meta, path = rec.split("\t", 1)
        entries.append((meta.split()[2], path))
    proc = subprocess.Popen(["git", "cat-file", "--batch"], cwd=dest,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    for sha, path in entries:
        # one at a time, so neither pipe fills up and blocks
        proc.stdin.write((sha + "\n").encode())
        proc.stdin.flush()
        header = proc.stdout.readline().split()
        size = int(header[2])
        data = proc.stdout.read(size)
        proc.stdout.read(1)  # trailing newline
        split, cls, name = path.split("/", 2)
        out = out_root / split / cls / safe_name(name)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    proc.stdin.close()
    proc.wait()
    (out_root / ".exported").write_text(f"{len(entries)} files\n")
    print(f"  plantdoc: wrote {len(entries)} files")


def get_tomato_village(raw):
    base = "Variant-a(Multiclass Classification)"
    paths = [f"{base}/{split}/{d}" for split in ("train", "val", "test") for d in TOMATO_VILLAGE_DIRS]
    sparse_clone("https://github.com/mamta-joshi-gehlot/Tomato-Village.git", raw / "tomato_village", paths)


def get_plantseg(raw):
    zpath = raw / "plantseg" / "plantseg.zip"
    if fetch(PLANTSEG_URL, zpath, size=PLANTSEG_SIZE) or not (raw / "plantseg" / ".md5ok").exists():
        print("  checking md5 of plantseg.zip")
        if md5_of(zpath) != PLANTSEG_MD5:
            raise RuntimeError("plantseg.zip md5 mismatch, delete it and run again")
        (raw / "plantseg" / ".md5ok").write_text("ok\n")
    extract(zpath, raw / "plantseg" / "extracted")


def get_indonesia(raw):
    meta = get_json(MENDELEY_API.format(id="ptz377bwb8"))
    dest = raw / "potato_indonesia"
    n = 0
    for f in meta["files"]:
        cls = INDONESIA_FOLDERS.get(f.get("folder_id"))
        if cls is None:
            continue
        cd = f["content_details"]
        if fetch(cd["download_url"], dest / cls / f["filename"], size=f["size"], sha256=cd.get("sha256_hash")):
            n += 1
    print(f"  potato_indonesia: {n} new files")


def get_ethiopia(raw):
    meta = get_json(MENDELEY_API.format(id="v4w72bsts5") + "/files?folder_id=root&version=2")
    dest = raw / "potato_ethiopia"
    for f in meta:
        cd = f["content_details"]
        out = dest / f["filename"]
        fetch(cd["download_url"], out, size=f["size"], sha256=cd.get("sha256_hash"))
        extract(out, dest / "extracted")


SOURCES = {
    "plantvillage": get_plantvillage,
    "plantdoc": get_plantdoc,
    "tomato_village": get_tomato_village,
    "potato_indonesia": get_indonesia,
    "potato_ethiopia": get_ethiopia,
    "plantseg": get_plantseg,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="data folder outside the repo")
    ap.add_argument("--only", nargs="*", choices=list(SOURCES), help="just these sources")
    args = ap.parse_args()
    raw = Path(args.root) / "raw"
    failed = []
    for name in args.only or SOURCES:
        print(f"== {name}")
        try:
            SOURCES[name](raw)
        except Exception as e:
            print(f"  FAILED: {e}")
            failed.append(name)
    if failed:
        print("failed:", ", ".join(failed))
        sys.exit(1)
    print("all done")


if __name__ == "__main__":
    main()
