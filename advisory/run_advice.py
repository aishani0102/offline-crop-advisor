"""Offline advice runner: INTERFACE JSON in, safe advice out.

Loads the Llama 3.2 1B .pte with the ExecuTorch Python runtime, builds the
prompt from the KB, streams the answer, runs the safety checks and prints
the timing and memory numbers.

Example:
  python advisory/run_advice.py --case advisory/examples/tomato_early_blight_moderate_en.json \
      --model /llama/spinquant/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8.pte \
      --tokenizer /llama/spinquant/tokenizer.model

Needs no network. The ExecuTorch Windows wheel (1.5.1) does not include the
Llama kernels (custom_sdpa, update_cache, embedding_byte), so on Windows we
run this inside the Linux container described in advisory/README.md.
"""

import argparse
import json
import re
import sys
import time

from knowledge import load_case, load_kb
from memory import available_mb, choose_mode
from prompt import build_messages, clean_output, to_llama3_text
from safety import safe_advice
from template import template_advice

SPECIAL = {
    "<|begin_of_text|>": 128000,
    "<|end_of_text|>": 128001,
    "<|start_header_id|>": 128006,
    "<|end_header_id|>": 128007,
    "<|eot_id|>": 128009,
}
STOP_IDS = {128001, 128008, 128009}


def peak_rss_mb():
    """Peak resident memory of this process in MB."""
    try:
        import resource
        kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return kb / 1024 if sys.platform != "darwin" else kb / (1024 * 1024)
    except ImportError:
        import psutil
        return psutil.Process().memory_info().peak_wset / (1024 * 1024)


class LlamaRunner:
    def __init__(self, model_path, tokenizer_path):
        t0 = time.time()
        import torch  # noqa: F401  (loads libtorch for the pybindings)
        import executorch.extension.llm.custom_ops.custom_ops  # noqa: F401
        import executorch.kernels.quantized  # noqa: F401
        from executorch.extension.pybindings import portable_lib
        from pytorch_tokenizers import TiktokenTokenizer

        self.torch = torch
        self.tok = TiktokenTokenizer(model_path=tokenizer_path)
        self.module = portable_lib._load_for_executorch(model_path)
        self.max_len = int(self.module.run_method("get_max_seq_len", ())[0])
        self.load_s = time.time() - t0
        # The first forward call is very slow (we measured over a minute on the
        # laptop) because the runtime pages in and prepares the weights. Do it
        # once here, like the app would at start-up, and time it separately.
        # Its KV cache entry at position 0 is overwritten by the real prompt.
        t1 = time.time()
        self._forward([SPECIAL["<|begin_of_text|>"]], 0)
        self.warmup_s = time.time() - t1

    def encode_chat(self, text):
        ids = []
        for part in re.split(r"(<\|[a-z_]+\|>)", text):
            if not part:
                continue
            if part in SPECIAL:
                ids.append(SPECIAL[part])
            else:
                ids += self.tok.encode(part, bos=False, eos=False)
        return ids

    def _forward(self, ids, pos):
        t = self.torch
        out = self.module.forward((t.tensor([ids], dtype=t.long), t.tensor([pos], dtype=t.long)))
        return int(out[0][0].argmax())

    def generate(self, prompt_ids, max_new_tokens=200, on_text=None):
        """Greedy decoding. Returns (text, stats)."""
        if len(prompt_ids) + max_new_tokens > self.max_len:
            raise ValueError(f"prompt too long: {len(prompt_ids)} tokens")
        t0 = time.time()
        nxt = self._forward(prompt_ids, 0)
        t_first = time.time()
        pos = len(prompt_ids)
        out_ids, shown = [], ""
        stopped = False
        while True:
            if nxt in STOP_IDS:
                stopped = True
                break
            out_ids.append(nxt)
            text = self.tok.decode(out_ids)
            # Hindi characters can span tokens; wait until the bytes are complete.
            if on_text and not text.endswith("�"):
                on_text(text[len(shown):])
                shown = text
            if len(out_ids) >= max_new_tokens:
                break
            nxt = self._forward([nxt], pos)
            pos += 1
        t_end = time.time()
        n = len(out_ids)
        stats = {
            "prompt_tokens": len(prompt_ids),
            "new_tokens": n,
            "ttft_s": round(t_first - t0, 3),
            "decode_tok_per_s": round((n - 1) / (t_end - t_first), 2) if n > 1 else None,
            "gen_total_s": round(t_end - t0, 3),
            "truncated": not stopped,
        }
        return self.tok.decode(out_ids), stats


def advise(case, runner=None, kb=None, max_new_tokens=200, stream=None, question=None):
    """Full advisory step for one case. Returns a result dict."""
    kb = kb or load_kb()
    if runner is None or case["uncertain"]:
        # Uncertain cases never go to Llama: in testing it made up a crop and a
        # problem ("wheat, pest infestation"). The template gives the KB text,
        # a retake tip and the referral, with no diagnosis.
        return {"advice": template_advice(case, kb), "mode": "template",
                "reason": "uncertain" if case["uncertain"] else "no model",
                "fails": [], "fallback": False, "raw": None, "stats": {}}
    messages, facts = build_messages(case, kb, question=question)
    ids = runner.encode_chat(to_llama3_text(messages))
    raw, stats = runner.generate(ids, max_new_tokens, on_text=stream)
    final, fails, fallback = safe_advice(clean_output(raw), case, kb, truncated=stats["truncated"])
    return {"advice": final, "mode": "llm", "fails": fails, "fallback": fallback,
            "raw": raw, "stats": stats}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--case", required=True, help="INTERFACE JSON file")
    ap.add_argument("--model", help=".pte file")
    ap.add_argument("--tokenizer", help="tokenizer.model file")
    ap.add_argument("--mode", choices=["auto", "llm", "template"], default="auto")
    ap.add_argument("--max-new-tokens", type=int, default=200)
    ap.add_argument("--question", help="optional follow-up question from the farmer")
    ap.add_argument("--json-out", help="write the result here")
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    case = load_case(args.case)
    kb = load_kb()
    mode = args.mode
    if mode == "auto":
        free = available_mb()
        mode = choose_mode(free) if args.model else "template"
        print(f"[free RAM {free:.0f} MB, mode {mode}]" if free else f"[mode {mode}]")

    runner = None
    if mode == "llm":
        if not (args.model and args.tokenizer):
            sys.exit("--model and --tokenizer are needed for llm mode")
        runner = LlamaRunner(args.model, args.tokenizer)
        print(f"[model loaded in {runner.load_s:.1f} s, first-call warm-up {runner.warmup_s:.1f} s]")
        print("--- model output (streamed, before safety check) ---")

    t0 = time.time()
    res = advise(case, runner, kb, args.max_new_tokens,
                 stream=lambda s: print(s, end="", flush=True), question=args.question)
    res["total_s"] = round(time.time() - t0, 3)
    res["peak_rss_mb"] = round(peak_rss_mb(), 1)
    if runner:
        res["stats"]["load_s"] = round(runner.load_s, 2)
        res["stats"]["warmup_s"] = round(runner.warmup_s, 2)
        print()
        print(f"--- safety: {'FAILED ' + str(res['fails']) + ', using KB template' if res['fallback'] else 'passed'} ---")
    print("--- advice shown to the farmer ---")
    print(res["advice"])
    s = res["stats"]
    if s:
        print("--- numbers ---")
        print(f"prompt tokens {s['prompt_tokens']}, new tokens {s['new_tokens']}, "
              f"time to first token {s['ttft_s']} s, decode {s['decode_tok_per_s']} tok/s, "
              f"total {res['total_s']} s, peak RAM {res['peak_rss_mb']} MB")
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
