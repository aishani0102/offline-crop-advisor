"""Pick Llama or template-only mode from the free RAM.

LLAMA_PEAK_MB is the peak resident memory we measured for the whole
runner process with the SpinQuant .pte (see docs/results/advisory_eval.md).
We ask for that plus a margin, so the phone does not start killing apps
while Llama runs. Below that we use the template, which needs almost no
memory and gives the same KB facts.
"""

LLAMA_PEAK_MB = 2032   # measured peak RSS, x86 laptop, eval run of 21 Nov 2026
MARGIN_MB = 512


def choose_mode(available_mb, peak_mb=LLAMA_PEAK_MB, margin_mb=MARGIN_MB):
    """Return "llm" if there is room for Llama, otherwise "template"."""
    if available_mb is None:
        return "template"
    return "llm" if available_mb >= peak_mb + margin_mb else "template"


def available_mb():
    """Free RAM on this machine in MB, or None if we cannot tell."""
    try:
        import psutil
        return psutil.virtual_memory().available / (1024 * 1024)
    except Exception:
        return None
