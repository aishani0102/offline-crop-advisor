"""Load the knowledge base and check the detection JSON.

Everything the advisory side says comes from advisory/kb/kb.json. This file
also picks which KB facts fit a case (label, severity, uncertain, language),
so the prompt, the template and the safety check all use the same facts.
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
KB_PATH = HERE / "kb" / "kb.json"
CLASSES_PATH = REPO / "configs" / "classes.json"

BANDS = ("none", "mild", "moderate", "severe")
LANGS = ("en", "hi")


def load_kb(path=KB_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_classes(path=CLASSES_PATH):
    with open(path, encoding="utf-8") as f:
        return {c["label"]: c for c in json.load(f)["classes"]}


def load_case(path):
    with open(path, encoding="utf-8") as f:
        return check_case(json.load(f))


def check_case(case):
    """Check the INTERFACE.md object and fill safe defaults.

    Anything odd (unknown label, crop that does not match, missing band)
    makes the case uncertain, because then we should not name a treatment.
    """
    classes = load_classes()
    case = dict(case)
    case.setdefault("language", "en")
    if case["language"] not in LANGS:
        case["language"] = "en"
    label = case.get("label")
    problems = []
    if label not in classes:
        problems.append("unknown label")
    else:
        cls = classes[label]
        for key in ("crop", "condition", "type"):
            if case.get(key) not in (None, cls[key]):
                problems.append(f"{key} does not match classes.json")
            case[key] = cls[key]
    band = case.get("severity_band")
    if band not in BANDS:
        problems.append("missing or unknown severity_band")
        case["severity_band"] = None
    if case.get("type") == "healthy":
        case["severity_band"] = "none"
    elif band == "none" and label in classes:
        problems.append("severity_band none on a disease or pest label")
    if problems:
        case["uncertain"] = True
    case["problems"] = problems
    case["uncertain"] = bool(case.get("uncertain", False))
    return case


def needs_referral(case):
    return case["uncertain"] or case.get("severity_band") == "severe"


def pct_text(case):
    pct = case.get("severity_pct")
    if pct is None:
        return None
    return str(int(round(float(pct))))


def _chem_line(chem, lang, kb):
    dose = chem["dose"][lang]
    if lang == "hi":
        name = f"{chem['name_hi']} ({chem['product']})"
        wait = (f"तुड़ाई से {chem['waiting_days']} दिन पहले तक छिड़काव न करें"
                if chem.get("waiting_days") else "प्रतीक्षा अवधि लेबल पर देखें")
    else:
        name = chem["product"]
        wait = (f"do not spray in the last {chem['waiting_days']} days before harvest"
                if chem.get("waiting_days") else "check the waiting period on the label")
    return f"{name}: {dose}, {wait}"


def select_facts(case, kb=None, compact=False):
    """Return the KB facts for this case as a dict of short text pieces.

    compact=True keeps fewer items, for the model prompt. A 1B model on a phone
    is slow to read a long prompt, and Hindi text takes about three times the
    tokens of English.

    Rules:
    - healthy: description plus prevention tips, no chemicals.
    - uncertain: no treatment at all, ask for a retake or KVK visit.
    - mild: cultural steps only.
    - moderate and severe: cultural steps plus the chemicals from the KB.
    - severe or uncertain: add the referral line.
    """
    kb = kb or load_kb()
    lang = case["language"]
    facts = {"lang": lang, "chemicals": [], "steps": [], "signs": []}
    entry = kb["entries"].get(case.get("label"))

    if case["uncertain"] or entry is None:
        facts["kind"] = "uncertain"
        facts["summary"] = kb["uncertain"][lang]
        facts["referral"] = kb["referral"][lang]
        return facts

    facts["entry"] = entry
    facts["title"] = title(case, lang)
    facts["summary"] = entry["description"][lang]
    if case["type"] == "healthy":
        facts["kind"] = "healthy"
        facts["steps"] = entry["cultural_ipm"][lang][:3 if compact else 4]
        facts["watch"] = entry["call_kvk"][lang]
        return facts

    band = case["severity_band"]
    facts["kind"] = band
    facts["signs"] = entry["recognise"][lang][:1 if compact else 2]
    facts["steps"] = entry["cultural_ipm"][lang][:2 if compact else 3]
    facts["severity_note"] = entry["severity"][band][lang]
    if band in ("moderate", "severe"):
        chems = entry["chemicals"][:2] if compact else entry["chemicals"]
        facts["chemicals"] = [_chem_line(c, lang, kb) for c in chems]
        facts["chem_names"] = entry["chemicals"]
        facts["chemical_note"] = entry["chemical_note"][lang]
        if entry["chemicals"]:
            facts["safety"] = kb["general_safety"][lang][1:2] if compact else kb["general_safety"][lang][:2]
        else:
            facts["no_dose"] = kb["no_dose_text"][lang]
    if band == "severe":
        facts["referral"] = kb["referral"][lang]
    return facts


CROP_HI = {"tomato": "टमाटर", "potato": "आलू"}
COND_HI = {
    "Healthy": "स्वस्थ",
    "Early blight": "अगेती झुलसा (Early blight)",
    "Late blight": "पछेती झुलसा (Late blight)",
    "Leaf miner": "पत्ती सुरंगक कीट (Leaf miner)",
    "Leaf mold": "पत्ती फफूंद (Leaf mold)",
    "Septoria leaf spot": "सेप्टोरिया पत्ती धब्बा (Septoria leaf spot)",
    "Yellow leaf curl virus": "पत्ती मोड़क वायरस (Leaf curl virus)",
}
BAND_HI = {"mild": "हल्का", "moderate": "मध्यम", "severe": "गंभीर"}


def title(case, lang):
    pct = pct_text(case)
    if lang == "hi":
        t = f"{CROP_HI[case['crop']]}: {COND_HI[case['condition']]}"
        if case["severity_band"] in BAND_HI:
            t += f", {BAND_HI[case['severity_band']]}"
            if pct is not None:
                t += f" (पत्ती का लगभग {pct}%)"
        return t
    t = f"{case['crop'].capitalize()}: {case['condition'].lower()}"
    if case["severity_band"] in ("mild", "moderate", "severe"):
        t += f", {case['severity_band']}"
        if pct is not None:
            t += f" (about {pct}% of the leaf)"
    return t


def facts_text(facts):
    """All fact text in one string, used by the safety check as the allowed source."""
    parts = [facts.get("title", ""), facts.get("summary", ""), facts.get("severity_note", ""),
             facts.get("chemical_note", ""), facts.get("no_dose", ""), facts.get("referral", ""),
             facts.get("watch", "")]
    parts += facts.get("signs", []) + facts.get("steps", []) + facts.get("chemicals", [])
    parts += facts.get("safety", [])
    return "\n".join(p for p in parts if p)
