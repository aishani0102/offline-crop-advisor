"""Run the adversarial set through the same path the app uses.

Each case has a tricky farmer question and a hand-written risky model
output. Uncertain cases never reach the model, so their output is ignored
and the template is used. Everything else goes through safety.py.

Run: python advisory/tests/test_adversarial.py
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from knowledge import check_case, load_kb  # noqa: E402
from safety import check_output, safe_advice  # noqa: E402
from template import template_advice  # noqa: E402

GROUNDING = ("chemical_not_in_kb", "number_not_in_kb", "dose_not_in_kb", "dose_in_words")


def run():
    kb = load_kb()
    data = json.loads((HERE / "adversarial.json").read_text(encoding="utf-8"))
    rows = []
    for item in data["cases"]:
        case = check_case(item["case"])
        if case["uncertain"]:
            final, fails, path = template_advice(case, kb), [], "blocked before the model (uncertain)"
        else:
            final, fails, fallback = safe_advice(item["model_output"], case, kb)
            path = "fell back to template" if fallback else "model output shown"
        final_fails = check_output(final, case, kb, limit_length=False)
        leaked = [f for f in final_fails if f.startswith(GROUNDING)]
        rows.append((item["kind"], path, fails, leaked))
    return rows


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    rows = run()
    n = len(rows)
    caught = sum(1 for r in rows if r[2])
    blocked = sum(1 for r in rows if r[1].startswith("blocked"))
    shown = [r for r in rows if r[1] == "model output shown"]
    leaked = sum(1 for r in rows if r[3])
    for kind, path, fails, leak in rows:
        print(f"{kind:48s} | {path:36s} | {', '.join(fails) if fails else '-'}")
    print()
    print(f"cases: {n}")
    print(f"caught by safety.py: {caught}")
    print(f"blocked before the model (uncertain): {blocked}")
    print(f"model output shown: {len(shown)} ({', '.join(r[0] for r in shown)})")
    print(f"chemical or dose not in the verified KB reaching the farmer: {leaked} of {n}")
    sys.exit(1 if leaked else 0)
