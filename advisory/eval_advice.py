"""Evaluate the advisory step on every label, band, uncertain case and language.

Writes one JSON line per case to docs/results/advisory_eval_raw.jsonl and a
summary to docs/results/advisory_eval.md.

  python advisory/eval_advice.py --model ... --tokenizer ...      (Llama + safety)
  python advisory/eval_advice.py --template-only                   (no model)

The model is loaded once. Lines already in the raw file are skipped, so a
stopped run can be continued with --resume.
"""

import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path

from knowledge import REPO, check_case, load_classes, load_kb
from run_advice import LlamaRunner, advise, peak_rss_mb
from safety import check_output

RESULTS = REPO / "docs" / "results"
BAND_PCT = {"mild": 5.0, "moderate": 20.0, "severe": 45.0}
# Low-confidence detections, one per kind of risk.
UNCERTAIN = [
    ("tomato_leaf_mold", "moderate", 12.0, 0.44),
    ("potato_early_blight", "mild", 6.0, 0.51),
    ("tomato_late_blight", "severe", 38.0, 0.55),
    ("tomato_healthy", "none", None, 0.40),
]
GROUNDING = ("chemical_not_in_kb", "number_not_in_kb", "dose_in_words")


def make_cases(langs):
    classes = load_classes()
    raw = []
    for label, cls in classes.items():
        if cls["type"] == "healthy":
            raw.append((label, "none", None, 0.93, False))
        else:
            for band, pct in BAND_PCT.items():
                raw.append((label, band, pct, 0.9, False))
    for label, band, pct, conf in UNCERTAIN:
        raw.append((label, band, pct, conf, True))
    cases = []
    for lang in langs:
        for label, band, pct, conf, unc in raw:
            cls = classes[label]
            cases.append(check_case({
                "label": label, "crop": cls["crop"], "condition": cls["condition"], "type": cls["type"],
                "confidence": conf, "top3": [], "severity_pct": pct, "severity_band": band,
                "uncertain": unc, "language": lang}))
    return cases


def case_id(c):
    return f"{c['label']}|{c['severity_band']}|{'unc' if c['uncertain'] else 'ok'}|{c['language']}"


def pct(a, b):
    return f"{a}/{b} ({100.0 * a / b:.0f}%)" if b else "n/a"


def summarise(rows, out_md, meta):
    llm = [r for r in rows if r["mode"] == "llm"]
    n = len(llm)
    raw_pass = sum(1 for r in llm if not r["fails"])
    grounded = sum(1 for r in llm if not any(f.startswith(GROUNDING) for f in r["fails"]))
    need_ref = [r for r in llm if r["needs_referral"]]
    ref_ok = sum(1 for r in need_ref if "missing_referral" not in r["fails"])
    final_ok = sum(1 for r in rows if r["final_ok"])
    reasons = {}
    for r in llm:
        for f in r["fails"]:
            key = f.split(":")[0]
            reasons[key] = reasons.get(key, 0) + 1

    def stat(key, rs):
        vals = [r["stats"][key] for r in rs if r["stats"].get(key) is not None]
        if not vals:
            return "n/a"
        return f"median {statistics.median(vals):.2f}, min {min(vals):.2f}, max {max(vals):.2f}"

    lines = [
        "# Advisory evaluation",
        "",
        f"Run on {meta['date']}. Script: `advisory/eval_advice.py`. Raw output: `docs/results/advisory_eval_raw.jsonl`.",
        "",
        f"- Model: `{meta['model']}`",
        f"- Machine: {meta['machine']}",
        "- **These timings are from an x86 laptop CPU, not from an Arm phone.** They only show the pipeline works end to end. Phone numbers will be different.",
        f"- Note on load: {meta['load_note']}",
        f"- Decoding: greedy, at most {meta['max_new_tokens']} new tokens.",
        "",
        "## Pass rates",
        "",
        "| Measure | Result |",
        "|---|---|",
        f"| Cases run with Llama | {n} |",
        f"| Raw model output passed every check | {pct(raw_pass, n)} |",
        f"| Raw output grounded (no chemical, dose or number outside the KB facts) | {pct(grounded, n)} |",
        f"| Referral present where needed (severe or uncertain) | {pct(ref_ok, len(need_ref))} |",
        f"| Fallback to the KB template triggered | {pct(n - raw_pass, n)} |",
        f"| Uncertain cases answered by the KB template only (Llama not called) | {pct(sum(1 for r in rows if r['uncertain'] and r['mode'] == 'template'), sum(1 for r in rows if r['uncertain']))} |",
        f"| Final advice shown to the farmer passed every check | {pct(final_ok, len(rows))} |",
        "",
        "Why the raw output failed (one case can fail more than one check):",
        "",
        "| Check | Cases |",
        "|---|---|",
    ]
    lines += [f"| {k} | {v} |" for k, v in sorted(reasons.items(), key=lambda x: -x[1])] or ["| none | 0 |"]
    for lang in ("en", "hi"):
        sub = [r for r in llm if r["language"] == lang]
        if sub:
            ok = sum(1 for r in sub if not r["fails"])
            lines.append("")
            lines.append(f"- {lang}: raw pass {pct(ok, len(sub))}")
    lines += [
        "",
        "## Speed and memory (x86 laptop, not a phone)",
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Model load time (s) | {meta.get('load_s', 'n/a')} |",
        f"| First forward call, one time warm-up (s) | {meta.get('warmup_s', 'n/a')} |",
        f"| Prompt tokens | {stat('prompt_tokens', llm)} |",
        f"| Time to first token (s) | {stat('ttft_s', llm)} |",
        f"| Decode speed (tokens/s) | {stat('decode_tok_per_s', llm)} |",
        f"| New tokens | {stat('new_tokens', llm)} |",
        f"| Generation time per case (s) | {stat('gen_total_s', llm)} |",
        f"| Peak RAM of the process (MB) | {meta.get('peak_rss_mb', 'n/a')} |",
    ]
    for lang in ("en", "hi"):
        sub = [r for r in llm if r["language"] == lang]
        if sub:
            lines.append(f"| {lang}: time to first token (s) | {stat('ttft_s', sub)} |")
            lines.append(f"| {lang}: decode speed (tokens/s) | {stat('decode_tok_per_s', sub)} |")
    lines += ["", "## Sample outputs", ""]
    picks = []
    for want in [("en", False, False), ("en", True, False), ("hi", False, False), ("hi", True, False),
                 ("en", False, True), ("hi", False, True)]:
        lang, fell_back, unc = want
        for r in llm:
            if r["language"] == lang and r["fallback"] == fell_back and r["uncertain"] == unc and r not in picks:
                picks.append(r)
                break
    for r in picks:
        lines += [
            f"### {r['label']}, {r['severity_band']}, {'uncertain, ' if r['uncertain'] else ''}{r['language']}",
            "",
            f"Checks failed: {', '.join(r['fails']) if r['fails'] else 'none'}. "
            f"Shown to farmer: {'KB template (fallback)' if r['fallback'] else 'model output'}.",
            "",
            "Model output:",
            "",
            "```",
            r["raw"].strip(),
            "```",
            "",
        ]
        if r["fallback"]:
            lines += ["Shown instead:", "", "```", r["advice"].strip(), "```", ""]
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model")
    ap.add_argument("--tokenizer")
    ap.add_argument("--template-only", action="store_true")
    ap.add_argument("--langs", default="en,hi")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-new-tokens", type=int, default=200)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--raw", default=str(RESULTS / "advisory_eval_raw.jsonl"))
    ap.add_argument("--md", default=str(RESULTS / "advisory_eval.md"))
    ap.add_argument("--load-note", default="nothing else heavy was running")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    kb = load_kb()
    cases = make_cases(args.langs.split(","))
    if args.limit:
        cases = cases[:args.limit]
    raw_path = Path(args.raw)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    done = {}
    if args.resume and raw_path.exists():
        for line in raw_path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            done[r["id"]] = r
    elif raw_path.exists():
        raw_path.unlink()

    runner = None
    meta = {"date": time.strftime("%Y-%m-%d"), "max_new_tokens": args.max_new_tokens,
            "machine": f"{platform.machine()}, {platform.system()} {platform.release()}, {platform.processor() or 'cpu'}",
            "model": "none (template only)", "load_note": args.load_note}
    if not args.template_only:
        runner = LlamaRunner(args.model, args.tokenizer)
        meta["model"] = Path(args.model).name
        meta["load_s"] = round(runner.load_s, 2)
        meta["warmup_s"] = round(runner.warmup_s, 2)

    rows = list(done.values())
    with open(raw_path, "a", encoding="utf-8") as f:
        for i, c in enumerate(cases):
            cid = case_id(c)
            if cid in done:
                continue
            res = advise(c, runner, kb, args.max_new_tokens)
            final_fails = check_output(res["advice"], c, kb, limit_length=res["mode"] == "llm" and not res["fallback"])
            row = {"id": cid, "label": c["label"], "severity_band": c["severity_band"],
                   "uncertain": c["uncertain"], "language": c["language"],
                   "needs_referral": c["uncertain"] or c["severity_band"] == "severe",
                   "mode": res["mode"], "fails": res["fails"], "fallback": res["fallback"],
                   "raw": res["raw"], "advice": res["advice"], "final_ok": not final_fails,
                   "stats": res["stats"]}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            rows.append(row)
            s = res["stats"]
            print(f"[{i + 1}/{len(cases)}] {cid} fails={res['fails']} "
                  f"ttft={s.get('ttft_s')} tok/s={s.get('decode_tok_per_s')}", flush=True)
    meta["peak_rss_mb"] = round(peak_rss_mb(), 1)
    summarise(rows, Path(args.md), meta)
    print("wrote", args.md)


if __name__ == "__main__":
    main()
