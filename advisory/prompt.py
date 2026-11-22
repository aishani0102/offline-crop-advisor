"""Build the Llama 3.2 Instruct prompt for one case.

The model only gets the KB facts picked for this case and is told to
rewrite them in simple words. It never sees the whole KB, so it has no
other chemical names or doses to copy from.
"""

import re

from knowledge import load_kb, select_facts

WORD_LIMIT = {"en": 120, "hi": 80}
LANG_NAME = {"en": "English", "hi": "simple Hindi (Devanagari script)"}

# The rules are in English for both languages. They are shorter in tokens,
# and the 1B model follows English instructions better. Only the answer
# language changes.
SYSTEM = (
    "You help small farmers in India. Rewrite the FACTS as short, simple advice for a farmer, "
    "in {lang}. Rules: use only the FACTS. Do not add any chemical, product, dose or number that is "
    "not in the FACTS. Do not add new advice. Start by naming the crop and the problem. "
    "Write {words} words or less, in plain sentences, no headings."
)

END_WITH = "End with this exact sentence: "
HEALTHY_HINT = "The leaf is healthy. Give a short reassurance and two or three prevention tips."
UNCERTAIN_HINT = "The app is not sure what the problem is. Do not name any treatment or chemical."
QUESTION = "Farmer's question (answer only from the FACTS): "


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
    facts = select_facts(case, kb, compact=True)
    lang = facts["lang"]
    system = SYSTEM.format(lang=LANG_NAME[lang], words=WORD_LIMIT[lang])
    user = "FACTS:\n" + facts_block(facts)
    if facts["kind"] == "healthy":
        user += "\n\n" + HEALTHY_HINT
    if facts["kind"] == "uncertain":
        user += "\n\n" + UNCERTAIN_HINT
    if question:
        # A follow-up from the farmer. It is answered only from the same FACTS.
        user += "\n\n" + QUESTION + question.strip()
    if facts.get("referral"):
        user += "\n\n" + END_WITH + facts["referral"]
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    return messages, facts


PREAMBLE = re.compile(r"^\s*(here is|here's|sure|okay|ok,|यहां|यहाँ|ज़रूर|जरूर)[^\n]*:\s*\n", re.IGNORECASE)


def clean_output(text):
    """Drop a chatty first line such as "Here is the rewritten advice:"."""
    return PREAMBLE.sub("", text, count=1).strip()


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
