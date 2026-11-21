"""Build the Llama 3.2 Instruct prompt for one case.

The model only gets the KB facts picked for this case and is told to
rewrite them in simple words. It never sees the whole KB, so it has no
other chemical names or doses to copy from.
"""

from knowledge import load_kb, select_facts

WORD_LIMIT = {"en": 120, "hi": 80}

SYSTEM = {
    "en": (
        "You help small farmers in India. Rewrite the FACTS below as short, simple advice for a farmer, "
        "in English. Rules: use only the FACTS. Do not add any chemical, product, dose or number that is "
        "not in the FACTS. Do not add new advice. Write {words} words or less, in plain sentences, no headings."
    ),
    "hi": (
        "आप भारत के छोटे किसानों की मदद करते हैं। नीचे दिए गए FACTS को किसान के लिए छोटी, सरल सलाह के रूप में "
        "हिंदी में दोबारा लिखें। नियम: केवल FACTS का इस्तेमाल करें। कोई ऐसी दवा, उत्पाद, मात्रा या संख्या न जोड़ें "
        "जो FACTS में नहीं है। नई सलाह न जोड़ें। {words} शब्दों या उससे कम में, सरल वाक्यों में लिखें, शीर्षक नहीं।"
    ),
}

END_WITH = {
    "en": "End with this exact sentence: ",
    "hi": "आखिर में यह वाक्य ज्यों का त्यों लिखें: ",
}

HEALTHY_HINT = {
    "en": "The leaf is healthy. Give a short reassurance and two or three prevention tips.",
    "hi": "पत्ती स्वस्थ है। किसान को छोटा सा भरोसा दें और बचाव के दो या तीन सुझाव दें।",
}

UNCERTAIN_HINT = {
    "en": "The app is not sure what the problem is. Do not name any disease treatment or chemical.",
    "hi": "ऐप को पक्का नहीं पता कि समस्या क्या है। किसी इलाज या दवा का नाम न लें।",
}


def facts_block(facts):
    lines = []
    if facts.get("title"):
        lines.append(facts["title"])
    lines.append(facts["summary"])
    lines += facts.get("signs", [])
    if facts.get("severity_note"):
        lines.append(facts["severity_note"])
    lines += facts.get("steps", [])
    if facts.get("watch"):
        lines.append(facts["watch"])
    if facts.get("chemicals"):
        lines.append(facts["chemical_note"])
        lines += facts["chemicals"]
        lines += facts.get("safety", [])
    if facts.get("no_dose"):
        lines.append(facts["no_dose"])
    return "\n".join("- " + l for l in lines)


def build_messages(case, kb=None, question=None):
    """Return (messages, facts). messages is a list of {role, content}."""
    kb = kb or load_kb()
    facts = select_facts(case, kb)
    lang = facts["lang"]
    system = SYSTEM[lang].format(words=WORD_LIMIT[lang])
    user = "FACTS:\n" + facts_block(facts)
    if facts["kind"] == "healthy":
        user += "\n\n" + HEALTHY_HINT[lang]
    if facts["kind"] == "uncertain":
        user += "\n\n" + UNCERTAIN_HINT[lang]
    if question:
        # A follow-up from the farmer. It is answered only from the same FACTS.
        q = {"en": "Farmer's question (answer only from the FACTS): ",
             "hi": "किसान का सवाल (केवल FACTS से जवाब दें): "}[lang]
        user += "\n\n" + q + question.strip()
    if facts.get("referral"):
        user += "\n\n" + END_WITH[lang] + facts["referral"]
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    return messages, facts


def to_llama3_text(messages):
    """Llama 3 chat format, as text. The runner turns the special tokens into ids."""
    out = "<|begin_of_text|>"
    for m in messages:
        out += f"<|start_header_id|>{m['role']}<|end_header_id|>\n\n{m['content'].strip()}<|eot_id|>"
    out += "<|start_header_id|>assistant<|end_header_id|>\n\n"
    return out


if __name__ == "__main__":
    import sys
    from knowledge import load_case
    msgs, _ = build_messages(load_case(sys.argv[1]))
    print(to_llama3_text(msgs))
