"""Check model output against the KB facts before a farmer sees it.

Checks:
1. chemicals: every pesticide or chemical name in the output must be in
   the facts given for this case (so none at all for healthy, mild or
   uncertain cases).
2. numbers: every number in the output must also appear in the facts
   (doses, waiting days, severity percent, helpline). Number words next to
   a unit ("two grams") are also caught.
3. names: the output may not name a crop or a problem that is not in the
   facts for this case (it once said "wheat, pest infestation").
4. referral: severe and uncertain cases must mention the KVK or the
   Kisan Call Centre number.
5. claims: no promise that the plant will be cured or that a result is
   guaranteed (the KB never promises this, and for the virus it says the
   opposite). English only for now.
6. form: not empty, right script for the language, not cut off, not too long.

If any check fails we throw the model text away and use the template,
which is written straight from the KB.
"""

import re

from knowledge import facts_text, load_kb, needs_referral, select_facts
from template import template_advice

# Names we look for. Lower case. The KB chemicals are added at load time.
# The extra names are common Indian pesticides a small model might invent;
# they are only here to be caught, not recommended.
EXTRA_CHEMICALS_EN = [
    "chlorpyrifos", "monocrotophos", "carbendazim", "carbofuran", "phorate", "profenofos",
    "cypermethrin", "endosulfan", "dimethoate", "acephate", "metalaxyl", "propineb", "hexaconazole",
    "tebuconazole", "difenoconazole", "propiconazole", "copper sulphate", "copper sulfate", "copper",
    "sulphur", "sulfur", "bordeaux", "streptocycline", "streptomycin", "emamectin", "spinosad",
    "chlorantraniliprole", "flubendiamide", "thiram", "zineb", "ziram", "maneb", "iprodione", "kitazin",
    "malathion", "quinalphos", "glyphosate", "paraquat", "2,4-d", "ddt", "methyl parathion", "parathion",
    "triazophos", "fipronil", "lambda-cyhalothrin", "cyhalothrin", "deltamethrin", "bifenthrin",
    "abamectin", "neem", "nske", "azadirachtin", "trichoderma", "pseudomonas", "fluxapyroxad",
    "pyraclostrobin", "trifloxystrobin", "famoxadone", "fenamidone", "mandipropamid", "metiram",
    "oxydemeton", "methyl demeton", "spiromesifen", "fenazaquin", "novaluron", "indoxacarb",
    "thiacloprid", "acetamiprid", "clothianidin", "dinotefuran", "buprofezin", "diafenthiuron",
    "pymetrozine", "aureofungin", "validamycin", "tricyclazole", "benomyl", "chlorothalonil",
    "captan", "mancozeb", "azoxystrobin", "cymoxanil", "cyazofamid", "dimethomorph", "imidacloprid",
    "thiamethoxam", "cyantraniliprole", "copper oxychloride", "urea", "dap", "potash",
    # Common Indian brand names. Brands are never in the KB, so these always fail.
    "bavistin", "blitox", "dithane", "indofil", "ridomil", "curzate", "confidor", "actara", "coragen",
    "kavach", "saaf", "nativo", "amistar", "antracol", "kocide", "sulfex", "nuvan", "rogor",
]
EXTRA_CHEMICALS_HI = [
    "क्लोरपायरीफॉस", "क्लोरपाइरीफॉस", "मोनोक्रोटोफॉस", "कार्बेन्डाजिम", "कार्बेंडाजिम", "कार्बोफ्यूरान",
    "फोरेट", "प्रोफेनोफॉस", "साइपरमेथ्रिन", "एंडोसल्फान", "डाइमेथोएट", "एसीफेट", "मेटालैक्सिल",
    "प्रोपिनेब", "हेक्साकोनाज़ोल", "हेक्साकोनाजोल", "टेबुकोनाज़ोल", "कॉपर", "तांबा", "गंधक", "सल्फर",
    "बोर्डो", "स्ट्रेप्टोसाइक्लिन", "इमामेक्टिन", "स्पिनोसैड", "क्लोरएन्ट्रानिलिप्रोल", "थीरम", "थायरम",
    "ज़िनेब", "जिनेब", "मैलाथियान", "क्विनालफॉस", "ग्लाइफोसेट", "पैराक्वाट", "फिप्रोनिल", "नीम",
    "ट्राइकोडर्मा", "क्लोरोथालोनिल", "कैप्टान", "मैंकोज़ेब", "मैन्कोज़ेब", "मैंकोजेब", "मेन्कोजेब",
    "एज़ोक्सीस्ट्रोबिन", "साइमोक्सानिल", "साइज़ोफ़ामिड", "डाइमेथोमॉर्फ", "इमिडाक्लोप्रिड",
    "थायामेथोक्साम", "थियामेथोक्सम", "साइएन्ट्रानिलिप्रोल", "यूरिया", "डीएपी", "पोटाश",
]
# Word endings that look like a pesticide name even if it is not in our list.
CHEM_SUFFIX = re.compile(
    r"\b[a-z]{3,}(?:zole|zol|strobin|carb|phos|fos|thrin|mectin|cloprid|thoxam|thalonil|"
    r"ozeb|zeb|neb|sulfan|thion|oxanil|famid|morph|uron|prole)\b"
)
NOT_CHEMICALS = {"thion"}

UNITS_EN = r"(?:g|gm|gram|grams|kg|ml|millilitre|millilitres|milliliter|litre|litres|liter|liters|l|lit|percent|%|ppm|acre|ha|hectare)"
UNITS_HI = r"(?:ग्राम|किलो|मिली|मिलीलीटर|लीटर|प्रतिशत|एकड़|हेक्टेयर)"
NUM_WORDS_EN = r"(?:one|two|three|four|five|six|seven|eight|nine|ten|twenty|fifty|hundred|half|quarter)"
NUM_WORDS_HI = r"(?:एक|दो|तीन|चार|पांच|पाँच|छह|सात|आठ|नौ|दस|बीस|पचास|सौ|आधा|आधी)"
WORD_DOSE = re.compile(
    rf"\b{NUM_WORDS_EN}\s+{UNITS_EN}\b|(?<!\S){NUM_WORDS_HI}\s+{UNITS_HI}", re.IGNORECASE
)

# Promises the KB never makes. "cannot be cured" and "no cure" do not match.
CURE_CLAIM = re.compile(
    r"\b(?:will|can|could|would|should|to)\s+(?:be\s+)?(?:fully\s+|completely\s+)?cure[ds]?\b"
    r"|\bcures\b|\bguarantee[ds]?\b|\b100\s*%\s*(?:cure|safe|effective|result)",
    re.IGNORECASE,
)

# Crops and problems the output may only name if the case facts name them.
CROPS = ["tomato", "potato", "wheat", "rice", "paddy", "maize", "corn", "cotton", "chilli", "chili",
         "brinjal", "eggplant", "onion", "soybean", "sugarcane", "mustard", "groundnut", "banana",
         "टमाटर", "आलू", "गेहूं", "गेहूँ", "धान", "चावल", "मक्का", "कपास", "मिर्च", "बैंगन", "प्याज",
         "सोयाबीन", "गन्ना", "सरसों", "मूंगफली", "केला"]
CONDITIONS = ["early blight", "late blight", "leaf mold", "leaf mould", "septoria", "leaf curl",
              "leaf miner", "powdery mildew", "downy mildew", "rust", "wilt", "mosaic", "bacterial spot",
              "anthracnose", "canker", "pest infestation", "nutrient deficiency", "root rot",
              "अगेती झुलसा", "पछेती झुलसा", "पत्ती फफूंद", "सेप्टोरिया", "पत्ती मोड़क", "पत्ती सुरंगक",
              "चूर्णिल आसिता", "रतुआ", "उकठा", "मोज़ेक", "विल्ट"]

HELPLINE_DIGITS = "18001801551"
KVK_WORDS = ["kvk", "krishi vigyan kendra", "कृषि विज्ञान केंद्र", "कृषि विज्ञान केन्द्र", "केवीके"]
CALL_CENTRE_WORDS = ["kisan call centre", "kisan call center", "किसान कॉल सेंटर"]

DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
MAX_WORDS = {"en": 170, "hi": 150}


def _kb_lexicon(kb):
    en, hi = set(EXTRA_CHEMICALS_EN), set(EXTRA_CHEMICALS_HI)
    for entry in kb["entries"].values():
        for c in entry["chemicals"]:
            for part in c["name"].split("+"):
                en.add(part.strip().lower())
            for part in c["name_hi"].split("+"):
                hi.add(part.strip())
    return sorted(en, key=len, reverse=True), sorted(hi, key=len, reverse=True)


def find_chemicals(text, kb):
    """Return the set of chemical-like names in text."""
    en, hi = _kb_lexicon(kb)
    low = text.lower()
    found = set()
    for name in en:
        if re.search(r"(?<![a-z])" + re.escape(name) + r"(?![a-z])", low):
            found.add(name)
    for name in hi:
        if name in text:
            found.add(name)
    for m in CHEM_SUFFIX.finditer(low):
        if m.group(0) not in NOT_CHEMICALS:
            found.add(m.group(0))
    # "copper oxychloride" also matches "copper"; keep only the longest match.
    return {f for f in found if not any(f != g and f in g for g in found)}


def wrong_names(text, source):
    """Crop or problem names in text that the case facts do not contain."""
    low, src = text.lower(), source.lower()
    bad = []
    for name in CROPS + CONDITIONS:
        n = name.lower()
        if re.search(r"(?<![a-z])" + re.escape(n) + r"(?![a-z])", low) and n not in src:
            bad.append(name)
    return bad


UNIT_MAP = {"g": "g", "gm": "g", "gram": "g", "grams": "g", "ग्राम": "g", "kg": "kg", "kilo": "kg",
            "kilogram": "kg", "kilograms": "kg", "किलो": "kg", "ml": "ml", "millilitre": "ml",
            "millilitres": "ml", "मिली": "ml", "l": "l", "lit": "l", "litre": "l", "litres": "l",
            "liter": "l", "liters": "l", "लीटर": "l", "%": "%", "percent": "%", "प्रतिशत": "%",
            "days": "day", "day": "day", "दिन": "day"}
DOSE_RE = re.compile(r"(\d+(?:\.\d+)?)(?:\s*(?:to|-|से)\s*(\d+(?:\.\d+)?))?\s*"
                     r"(kilograms|kilogram|millilitres|millilitre|grams|gram|litres|litre|liters|liter|"
                     r"percent|days|day|kilo|lit|gm|kg|ml|g|l|%|ग्राम|किलो|मिली|लीटर|प्रतिशत|दिन)(?![a-z])",
                     re.IGNORECASE)


def dose_pairs(text):
    """Set of (number, unit) pairs, so "4 kg" and "4 g" are different doses."""
    text = text.translate(DEVANAGARI_DIGITS)
    pairs = set()
    for a, b, unit in DOSE_RE.findall(text):
        u = UNIT_MAP[unit.lower()]
        pairs.add((a, u))
        if b:
            pairs.add((b, u))
    return pairs


def numbers(text):
    text = text.translate(DEVANAGARI_DIGITS)
    # Remove list markers like "1." or "2)" at the start of a line.
    text = re.sub(r"(?m)^\s*\d+[.)]\s+", "", text)
    text = text.replace("1800-180-1551", " HELPLINE ")
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def _has_referral(text):
    low = text.lower()
    digits = re.sub(r"\D", "", text.translate(DEVANAGARI_DIGITS))
    return (HELPLINE_DIGITS in digits or any(w in low for w in KVK_WORDS)
            or any(w in low for w in CALL_CENTRE_WORDS))


def _script_ok(text, lang):
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return False
    deva = sum(1 for ch in letters if "ऀ" <= ch <= "ॿ")
    share = deva / len(letters)
    return share >= 0.6 if lang == "hi" else share <= 0.05


def check_output(text, case, kb=None, facts=None, truncated=False, limit_length=True):
    """Return a list of failed check names (empty list means it passed).

    limit_length is off for the template, which lists every KB step on purpose.
    """
    kb = kb or load_kb()
    facts = facts or select_facts(case, kb)
    source = facts_text(facts)
    lang = facts["lang"]
    fails = []

    if not text or not text.strip():
        return ["empty"]

    allowed_chems = find_chemicals(source, kb)
    extra = {c for c in find_chemicals(text, kb) if c not in allowed_chems
             and not any(c in a or a in c for a in allowed_chems)}
    if extra:
        fails.append("chemical_not_in_kb:" + ",".join(sorted(extra)))

    allowed_nums = numbers(source)
    if case.get("severity_pct") is not None:
        allowed_nums |= numbers(str(case["severity_pct"]))
    bad_nums = {n for n in numbers(text) if n not in allowed_nums}
    if bad_nums:
        fails.append("number_not_in_kb:" + ",".join(sorted(bad_nums)))
    bad_pairs = dose_pairs(text) - dose_pairs(source)
    if bad_pairs:
        fails.append("dose_not_in_kb:" + ",".join(f"{a} {u}" for a, u in sorted(bad_pairs)))
    word_doses = [m.group(0) for m in WORD_DOSE.finditer(text) if m.group(0).lower() not in source.lower()]
    if word_doses:
        fails.append("dose_in_words:" + ",".join(word_doses))

    mismatch = wrong_names(text, source)
    if mismatch:
        fails.append("crop_or_condition_mismatch:" + ",".join(mismatch))

    if CURE_CLAIM.search(text):
        fails.append("cure_claim")

    if needs_referral(case) and not _has_referral(text):
        fails.append("missing_referral")

    if not _script_ok(text, lang):
        fails.append("wrong_language")
    if truncated:
        fails.append("cut_off")
    if limit_length and len(text.split()) > MAX_WORDS[lang]:
        fails.append("too_long")
    return fails


def safe_advice(text, case, kb=None, truncated=False):
    """Return (final_text, fails, used_fallback).

    fails are the checks the raw model text failed. If the only failure is a
    missing referral, the fixed KB referral sentence is added and the text is
    checked again (the app does the same). If that passes, the model text is
    kept and used_fallback is False.
    """
    kb = kb or load_kb()
    fails = check_output(text, case, kb, truncated=truncated)
    if fails == ["missing_referral"]:
        referral = select_facts(case, kb).get("referral", "")
        retried = text.strip() + "\n\n" + referral
        if referral and not check_output(retried, case, kb):
            return retried, fails, False
    if fails:
        return template_advice(case, kb), fails, True
    return text.strip(), fails, False


def referral_retried(fails, used_fallback):
    """True when the model text was kept only because the referral was added."""
    return fails == ["missing_referral"] and not used_fallback
