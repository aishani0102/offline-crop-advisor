"""Short referral text the farmer can send by normal SMS to the KVK or an
extension worker. SMS works without mobile data, so this step stays offline.

Only used for severe or uncertain cases. The village is left blank for the
farmer to fill in.

English is plain ASCII so it fits in one SMS (160 characters). Hindi needs
Unicode SMS, where one part holds 70 characters, so a Hindi message of up to
160 characters goes as 2 or 3 joined parts. Most phones join them.
"""

import datetime

from knowledge import BAND_HI, COND_HI, CROP_HI, needs_referral

MAX_CHARS = 160
VILLAGE_BLANK = "______"


def _short_cond_hi(condition):
    # "पछेती झुलसा (Late blight)" -> "पछेती झुलसा", to save characters.
    return COND_HI[condition].split(" (")[0]


def build_sms(case, date=None, lang=None):
    """Return the SMS text, or None if this case does not need a referral."""
    if not needs_referral(case):
        return None
    lang = lang or case.get("language", "en")
    date = date or datetime.date.today()
    d = date.strftime("%d-%m-%Y")
    pct = case.get("severity_pct")
    pct_txt = f" {int(round(float(pct)))}%" if pct is not None else ""
    band = case.get("severity_band")

    if lang == "hi":
        cond = _short_cond_hi(case["condition"])
        if case["uncertain"]:
            cond = f"शायद {cond} (पक्का नहीं)"
        sev = f", {BAND_HI[band]}{pct_txt}" if band in BAND_HI else ""
        text = (f"KVK सहायता: {CROP_HI[case['crop']]}, {cond}{sev}। "
                f"तारीख {d}, गांव {VILLAGE_BLANK}। कृपया सलाह दें।")
    else:
        cond = case["condition"].lower()
        if case["uncertain"]:
            cond = f"possible {cond} (unsure)"
        sev = f", {band}{pct_txt}" if band in ("mild", "moderate", "severe") else ""
        text = (f"KVK help: {case['crop']} {cond}{sev}. Date {d}, village {VILLAGE_BLANK}. "
                f"Seen by offline crop app. Please advise.")
        text = text.encode("ascii", "replace").decode("ascii")

    if len(text) > MAX_CHARS:
        raise ValueError(f"SMS too long ({len(text)} chars): {text}")
    return text


def sms_parts(text):
    """How many SMS parts the text needs (GSM 7 bit for ASCII, else Unicode)."""
    if all(ord(ch) < 128 for ch in text):
        return 1 if len(text) <= 160 else -(-len(text) // 153)
    return 1 if len(text) <= 70 else -(-len(text) // 67)


if __name__ == "__main__":
    import sys
    from knowledge import load_case
    case = load_case(sys.argv[1])
    for lang in ("en", "hi"):
        sms = build_sms(case, lang=lang)
        if sms is None:
            print("no referral needed for this case")
            break
        print(f"[{lang}] {len(sms)} chars, {sms_parts(sms)} SMS part(s): {sms}")
