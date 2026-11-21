"""Pack the two Mendeley potato datasets into one zip for Colab.

Mendeley sometimes refuses downloads from Colab. If that happens, run this on
a machine where download.py already worked, upload the zip to the cache
folder on Drive, and the Colab notebook unzips it before downloading the rest.

    python -I scripts/pack_potato_raw.py --root <data_root> --out potato_raw.zip
"""
import argparse
import zipfile
from pathlib import Path

SOURCES = ["potato_indonesia", "potato_ethiopia"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="data folder used by download.py")
    ap.add_argument("--out", default="potato_raw.zip")
    args = ap.parse_args()
    raw = Path(args.root) / "raw"

    n = 0
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_STORED) as z:
        for name in SOURCES:
            src = raw / name
            if not src.exists():
                raise SystemExit(f"{src} is missing, run download.py first")
            for f in sorted(src.rglob("*")):
                # skip half-finished downloads and the extracted Ethiopia copy,
                # download.py re-extracts the rar on its own
                if f.is_dir() or f.name.endswith(".part") or "extracted" in f.relative_to(src).parts:
                    continue
                z.write(f, f.relative_to(raw).as_posix())
                n += 1
            # tells download.py this source is complete, so it skips Mendeley
            z.writestr(f"{name}/.complete", "ok\n")
    print(f"wrote {n} files to {args.out}")


if __name__ == "__main__":
    main()
