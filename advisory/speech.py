"""Make advice text easy for Android's offline text-to-speech to read.

Removes list markers and symbols, spells out units and percent signs, and
reads the helpline digit by digit. Works for English and Hindi.
"""

import re

UNITS = {
    "en": [(r"(\d)\s*%", r"\1 percent"), (r"\bml\b", "millilitres"), (r"\bkg\b", "kilograms"),
           (r"(\d)\s*g\b", r"\1 grams"), (r"\bKVK\b", "K V K"), (r"\bWP\b", "W P"), (r"\bWG\b", "W G"),
           (r"\bSC\b", "S C"), (r"\bSL\b", "S L"), (r"\bOD\b", "O D"), (r"\bNSKE\b", "N S K E"),
           (r"\bTNAU\b", "T N A U"), (r"\+", " and ")],
    "hi": [(r"(\d)\s*%", r"\1 प्रतिशत"), (r"\bKVK\b", "के वी के"), (r"\bWP\b", "डब्ल्यू पी"),
           (r"\bWG\b", "डब्ल्यू जी"), (r"\bSC\b", "एस सी"), (r"\bSL\b", "एस एल"), (r"\bOD\b", "ओ डी"),
           (r"\bNSKE\b", "एन एस के ई"), (r"\bTNAU\b", "टी एन ए यू"), (r"\+", " और ")],
}
HELPLINE = "1800-180-1551"


def to_speech(text, lang="en"):
    # Read the helpline one digit at a time, in both languages.
    t = text.replace(HELPLINE, " ".join(HELPLINE.replace("-", "")))
    # List markers at the start of a line: "- ", "* ", "1. ", "2) "
    t = re.sub(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", "", t)
    for pat, rep in UNITS[lang]:
        t = re.sub(pat, rep, t)
    # Brackets and other symbols TTS reads out loud or stumbles on.
    t = re.sub(r"[()\[\]{}\"'*_#/\\|<>:;]", " ", t)
    # Hyphens between words become spaces ("purple-brown"), but keep "1.8".
    t = re.sub(r"(?<=\S)-(?=\S)", " ", t)
    # One sentence per line so the TTS engine pauses between them.
    t = re.sub(r"\s*\n\s*", ". ", t.strip())
    t = re.sub(r"([.!?।])(\s*[.।])+", r"\1", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


if __name__ == "__main__":
    import sys
    from knowledge import load_case
    from template import template_advice
    case = load_case(sys.argv[1])
    print(to_speech(template_advice(case), case["language"]))
