"""Get the Llama 3.2 1B Instruct .pte for the advisory step.

Weights are never in the repo (Llama 3.2 licence). Two ways to get the model:

1. download (what we used): the .pte that the ExecuTorch team built from
   Meta's SpinQuant INT4 checkpoint and published on Hugging Face as
   executorch-community/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8-ET.
   We pin the commit and check SHA-256 of every file.

     python advisory/export_llama.py download --out <data_root>/llama/spinquant

2. export: build our own .pte from Meta's gated SpinQuant (or QLoRA)
   checkpoint with the ExecuTorch Llama export flow, with a shorter
   context (1024 tokens) to save KV cache memory. Needs a Hugging Face
   login that has accepted the Llama 3.2 licence (huggingface-cli login).
   The script never reads or prints the token itself.

     python advisory/export_llama.py export --variant spinquant --out <data_root>/llama/own_export

   The export flags are the ones in the ExecuTorch team's published recipe
   for this checkpoint, except --max_seq_length and --max_context_length.

Using either file means you accept the Llama 3.2 Community Licence and
must show "Built with Llama" in the app.
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

PREBUILT_REPO = "executorch-community/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8-ET"
PREBUILT_REV = "911221e0f49d3354cbd4697a9c09feee25cadec7"
PREBUILT_FILES = {
    "Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8.pte":
        "8715cdba9e91f6bede00cc5f2d6b12397b95225da5630c4972a8da03001cda3b",
    "tokenizer.model": "82e9d31979e92ab929cd544440f129d9ecd797b69e327f80f17e1c50d5551b55",
    "params.json": None,
}

CHECKPOINTS = {
    "spinquant": ("meta-llama/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8",
                  ["--preq_mode", "8da4w_output_8da8w", "--preq_group_size", "32",
                   "--preq_embedding_quantize", "8,0", "--use_spin_quant", "native"]),
    "qlora": ("meta-llama/Llama-3.2-1B-Instruct-QLORA_INT4_EO8",
              ["--preq_mode", "8da4w_output_8da8w", "--preq_group_size", "32",
               "--preq_embedding_quantize", "8,0", "--use_qat", "--use_lora", "16"]),
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def download(out):
    out.mkdir(parents=True, exist_ok=True)
    for name, want in PREBUILT_FILES.items():
        dest = out / name
        if not dest.exists():
            url = f"https://huggingface.co/{PREBUILT_REPO}/resolve/{PREBUILT_REV}/{name}"
            print("downloading", url)
            tmp = dest.with_suffix(dest.suffix + ".part")
            with urllib.request.urlopen(url) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
            tmp.rename(dest)
        if want:
            got = sha256(dest)
            if got != want:
                sys.exit(f"SHA-256 mismatch for {name}: {got}")
            print("ok", name)
    print("model files in", out)


def export(out, variant, max_len):
    from huggingface_hub import snapshot_download  # uses the saved login, never prints it

    repo, flags = CHECKPOINTS[variant]
    ckpt_dir = out / "checkpoint"
    snapshot_download(repo, local_dir=str(ckpt_dir), allow_patterns=["*.pth", "params.json", "tokenizer.model"])
    name = f"llama3_2_1b_instruct_{variant}_int4_ctx{max_len}.pte"
    cmd = [
        sys.executable, "-m", "executorch.examples.models.llama.export_llama",
        "--model", "llama3_2",
        "--checkpoint", str(ckpt_dir / "consolidated.00.pth"),
        "--params", str(ckpt_dir / "params.json"),
        "--use_sdpa_with_kv_cache", "-X", "--xnnpack-extended-ops",
        "--max_seq_length", str(max_len), "--max_context_length", str(max_len),
        "-kv", "-d", "fp32",
        "--metadata", '{"get_bos_id":128000, "get_eos_ids":[128009, 128001]}',
        "--output_name", str(out / name),
    ] + flags
    print("running:", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=str(out))
    shutil.copy(ckpt_dir / "tokenizer.model", out / "tokenizer.model")
    print("wrote", out / name)


def main():
    ap = argparse.ArgumentParser(description="Download or export the Llama 3.2 1B .pte")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("download")
    d.add_argument("--out", type=Path, required=True)
    e = sub.add_parser("export")
    e.add_argument("--out", type=Path, required=True)
    e.add_argument("--variant", choices=sorted(CHECKPOINTS), default="spinquant")
    e.add_argument("--max-len", type=int, default=1024)
    args = ap.parse_args()
    if args.cmd == "download":
        download(args.out)
    else:
        args.out.mkdir(parents=True, exist_ok=True)
        export(args.out, args.variant, args.max_len)


if __name__ == "__main__":
    main()
