"""Advice written straight from the KB, with no language model.

Used when the model output fails a safety check, when the phone does not
have enough free memory for Llama, or when the model file is missing.
"""

from knowledge import load_kb, select_facts

LABELS = {
    "en": {"signs": "Signs", "do": "What to do", "spray": "If you need to spray, use one of these",
           "prevent": "To keep it healthy"},
    "hi": {"signs": "पहचान", "do": "क्या करें", "spray": "अगर छिड़काव ज़रूरी हो तो इनमें से कोई एक",
           "prevent": "फसल स्वस्थ रखने के लिए"},
}


def template_advice(case, kb=None):
    kb = kb or load_kb()
    facts = select_facts(case, kb)
    lang = facts["lang"]
    words = LABELS[lang]
    lines = []

    if facts["kind"] == "uncertain":
        lines.append(facts["summary"])
        lines.append(facts["referral"])
        return "\n".join(lines)

    lines.append(facts["title"] + ".")
    lines.append(facts["summary"])

    if facts["kind"] == "healthy":
        lines.append(words["prevent"] + ":")
        lines += ["- " + s for s in facts["steps"][:3]]
        lines.append(facts["watch"])
        return "\n".join(lines)

    lines.append(facts["severity_note"])
    lines.append(words["do"] + ":")
    lines += ["- " + s for s in facts["steps"]]
    if facts["chemicals"]:
        lines.append(words["spray"] + ":")
        lines += ["- " + c for c in facts["chemicals"]]
        lines += facts["safety"]
    elif facts.get("no_dose"):
        lines.append(facts["no_dose"])
    if facts.get("referral"):
        lines.append(facts["referral"])
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    from knowledge import load_case
    print(template_advice(load_case(sys.argv[1])))
