"""Tests for the SMS referral, the speech text and the memory mode picker.

Run: python advisory/tests/test_extras.py
"""

import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge import check_case, load_classes, load_kb  # noqa: E402
from memory import LLAMA_PEAK_MB, MARGIN_MB, choose_mode  # noqa: E402
from referral import build_sms, sms_parts  # noqa: E402
from speech import to_speech  # noqa: E402
from template import template_advice  # noqa: E402

DATE = datetime.date(2026, 11, 21)


def case(label, band, pct, uncertain=False, lang="en"):
    return check_case({"label": label, "severity_band": band, "severity_pct": pct,
                       "uncertain": uncertain, "language": lang})


def test_referral():
    # Every label, every band that needs a referral, both languages.
    n = 0
    for label, cls in load_classes().items():
        bands = [("none", None)] if cls["type"] == "healthy" else [("severe", 45.0), ("moderate", 20.0)]
        for band, pct in bands:
            for unc in (False, True):
                c = case(label, band, pct, unc)
                for lang in ("en", "hi"):
                    sms = build_sms(c, DATE, lang)
                    if band != "severe" and not unc:
                        assert sms is None
                        continue
                    assert len(sms) <= 160, sms
                    assert "21-11-2026" in sms and "______" in sms
                    if lang == "en":
                        assert sms.isascii() and sms_parts(sms) == 1, sms
                    n += 1
    print(f"referral: {n} messages ok")
    for c in [case("tomato_late_blight", "severe", 45.2), case("potato_early_blight", "mild", 6, True)]:
        for lang in ("en", "hi"):
            sms = build_sms(c, DATE, lang)
            print(f"  [{lang}] {len(sms)} chars, {sms_parts(sms)} part(s): {sms}")


def test_speech():
    kb = load_kb()
    bad = re.compile(r"[-*()%+:/]|\bml\b|\bKVK\b")
    for label in kb["entries"]:
        for lang in ("en", "hi"):
            band = "none" if label.endswith("healthy") else "severe"
            c = case(label, band, None if band == "none" else 45.0, lang=lang)
            spoken = to_speech(template_advice(c, kb), lang)
            left = bad.findall(spoken)
            assert not left, (label, lang, left, spoken)
            assert "\n" not in spoken
    print("speech: all labels ok")
    sample = to_speech(template_advice(case("tomato_early_blight", "severe", 45.0), kb), "en")
    print("  en:", sample[:300], "...")
    sample = to_speech(template_advice(case("tomato_early_blight", "severe", 45.0, lang="hi"), kb), "hi")
    print("  hi:", sample[:300], "...")


def test_memory():
    need = LLAMA_PEAK_MB + MARGIN_MB
    assert choose_mode(need) == "llm"
    assert choose_mode(need - 1) == "template"
    assert choose_mode(None) == "template"
    assert choose_mode(8000) == "llm" and choose_mode(1500) == "template"
    print(f"memory: llm mode needs {need} MB free")


if __name__ == "__main__":
    test_referral()
    test_speech()
    test_memory()
    print("all extras tests passed")
