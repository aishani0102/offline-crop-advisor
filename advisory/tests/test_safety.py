"""Tests for the safety checks and the template, using hand-written outputs.

Run: python advisory/tests/test_safety.py
No model is needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge import check_case, load_kb  # noqa: E402
from safety import check_output, safe_advice  # noqa: E402
from template import template_advice  # noqa: E402

KB = load_kb()


def case(label, band, pct=None, uncertain=False, lang="en", conf=0.9):
    return check_case({"label": label, "severity_band": band, "severity_pct": pct,
                       "uncertain": uncertain, "language": lang, "confidence": conf})


GOOD_MODERATE_EN = (
    "Your tomato has early blight. You will see brown spots with rings, like a target. "
    "Pick off the spotted leaves and destroy them, and rotate your crops. "
    "If it keeps spreading, spray Mancozeb 75% WG, 400 g in 200 litres of water per acre. "
    "Do not spray in the last 10 days before harvest. Wear gloves and a mask."
)

TESTS = [
    # (name, case, text, expected fail prefixes)
    ("good moderate", case("tomato_early_blight", "moderate", 18.5), GOOD_MODERATE_EN, []),
    ("invented chemical", case("tomato_early_blight", "moderate", 18.5),
     GOOD_MODERATE_EN + " You can also use chlorpyrifos.", ["chemical_not_in_kb"]),
    ("unknown chemical by suffix", case("tomato_early_blight", "moderate", 18.5),
     GOOD_MODERATE_EN + " Tebufenozole also works.", ["chemical_not_in_kb"]),
    ("wrong dose", case("tomato_early_blight", "moderate", 18.5),
     GOOD_MODERATE_EN.replace("400 g", "2.5 g per litre"), ["number_not_in_kb"]),
    ("dose in words", case("tomato_early_blight", "moderate", 18.5),
     GOOD_MODERATE_EN + " Use two grams per litre.", ["dose_in_words"]),
    ("chemical on a mild case", case("tomato_early_blight", "mild", 4),
     "Pick off spotted leaves. Spray mancozeb.", ["chemical_not_in_kb"]),
    ("severe without referral", case("potato_late_blight", "severe", 45),
     "Your potato has late blight. Remove the leaves and spray Mancozeb 75% WP.", ["missing_referral"]),
    ("severe with referral", case("potato_late_blight", "severe", 45),
     "Your potato has late blight and it is bad. Destroy the plant tops and spray Mancozeb 75% WP. "
     "Please show the plant to your KVK or call 1800-180-1551.", []),
    ("uncertain names a chemical", case("tomato_leaf_mold", "moderate", 12, uncertain=True),
     "Not sure. Try mancozeb. Visit your KVK.", ["chemical_not_in_kb"]),
    ("uncertain ok", case("tomato_leaf_mold", "moderate", 12, uncertain=True),
     "The app is not sure. Take a clear photo again or visit your KVK.", []),
    ("healthy with spray", case("tomato_healthy", "none"),
     "Your plant is healthy. Spray neem every week to be safe.", ["chemical_not_in_kb"]),
    ("healthy ok", case("tomato_healthy", "none"),
     "Good news, your tomato leaf looks healthy. Check the crop every week and use yellow sticky traps, "
     "10 per acre.", []),
    ("hindi good", case("tomato_septoria_leaf_spot", "moderate", 20, lang="hi"),
     "आपके टमाटर में सेप्टोरिया पत्ती धब्बा है। धब्बे वाली पत्तियां हटाएं। ज़रूरत हो तो मैंकोज़ेब 75% WP "
     "600 से 800 ग्राम, 300 लीटर पानी में, प्रति एकड़ छिड़कें।", []),
    ("hindi devanagari digits", case("tomato_septoria_leaf_spot", "moderate", 20, lang="hi"),
     "मैंकोज़ेब ५ ग्राम प्रति लीटर छिड़कें।", ["number_not_in_kb"]),
    ("hindi asked, english given", case("tomato_septoria_leaf_spot", "moderate", 20, lang="hi"),
     "Remove the spotted leaves.", ["wrong_language"]),
    ("cut off", case("tomato_early_blight", "moderate", 18.5), GOOD_MODERATE_EN, ["cut_off"]),
]


def run():
    failed = 0
    for name, c, text, expected in TESTS:
        fails = check_output(text, c, KB, truncated=(name == "cut off"))
        got = sorted({f.split(":")[0] for f in fails})
        ok = got == sorted(expected)
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {fails}")

    # The template must always pass its own checks, for every label, band and language.
    for label, entry in KB["entries"].items():
        bands = ["none"] if entry["type"] == "healthy" else ["mild", "moderate", "severe"]
        for band in bands:
            for lang in ("en", "hi"):
                for unc in (False, True):
                    c = case(label, band, None if band == "none" else 25, uncertain=unc, lang=lang)
                    fails = check_output(template_advice(c, KB), c, KB, limit_length=False)
                    if fails:
                        failed += 1
                        print("FAIL  template", label, band, lang, unc, fails)
    final, fails, fallback = safe_advice("Use chlorpyrifos 5 ml.", case("tomato_early_blight", "moderate", 18.5), KB)
    assert fallback and "chlorpyrifos" not in final.lower()
    print("template checks done")
    print("failed:", failed)
    return failed


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
