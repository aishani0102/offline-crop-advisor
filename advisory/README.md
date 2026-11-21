# Advisory stage

This stage takes the detection result (the JSON object in `docs/INTERFACE.md`) and gives the farmer short advice in English or Hindi. Llama 3.2 1B Instruct (4-bit, ExecuTorch with XNNPACK) rewrites facts from our verified knowledge base in simple words. It does not decide what to spray. Every chemical name and dose comes from `kb/kb.json`, and a safety check runs on every answer before the farmer sees it.

## Files

| File | What it does |
|---|---|
| `kb/kb.json` | One entry per class: description, signs, IPM steps, chemicals with dose and waiting period, severity notes, when to call the KVK. English and Hindi. |
| `kb/SOURCES.md` | Every source we used, and the gaps. |
| `knowledge.py` | Loads the KB, checks the input JSON, picks the facts for a case. |
| `prompt.py` | Builds the Llama 3.2 chat prompt from those facts. |
| `safety.py` | Checks the model output and falls back to the template if a check fails. |
| `template.py` | Advice written straight from the KB, with no model. |
| `run_advice.py` | Offline runner: one JSON file in, advice and timing out. |
| `eval_advice.py` | Runs every label, band, uncertain case and language. Results go to `docs/results/advisory_eval.md`. |
| `export_llama.py` | Downloads or exports the .pte. |
| `memory.py` | Picks Llama or template-only mode from the free RAM. |
| `referral.py` | Short SMS text for the KVK in severe or uncertain cases. |
| `speech.py` | Cleans the advice so offline text-to-speech reads it well. |
| `tests/` | Tests that need no model, including `adversarial.json` (32 tricky cases) and `test_adversarial.py`. |

## Setup

Python 3.10. Model files stay outside the repo, in a folder we call `<data_root>` here.

```
python -m venv venv-advisory
venv-advisory\Scripts\activate
pip install -r advisory/requirements.txt
python advisory/export_llama.py download --out <data_root>/llama/spinquant
```

### Running Llama on a Windows laptop

The ExecuTorch 1.5.1 Windows wheel loads the .pte but has no Llama kernels (`custom_sdpa`, `update_cache`, `fast_hadamard_transform`, `embedding_byte`), so `forward` fails. The Linux wheel has them. On Windows we run the runner in a Linux container:

```
docker build -t advisory-et:1.5.1 advisory/docker
docker volume create advisory-llama
docker run --rm -v <data_root>/llama:/src:ro -v advisory-llama:/llama advisory-et:1.5.1 sh -c "mkdir -p /llama/spinquant && cp /src/spinquant/* /llama/spinquant/"
```

Copying the model into a Docker volume matters. Reading it straight from a Windows folder made the first call about three times slower in our test.

One case:

```
docker run --rm -v advisory-llama:/llama:ro -v <repo>:/repo advisory-et:1.5.1 python /repo/advisory/run_advice.py --mode llm --case /repo/advisory/examples/tomato_early_blight_moderate_en.json --model /llama/spinquant/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8.pte --tokenizer /llama/spinquant/tokenizer.model
```

Full evaluation (about 30 minutes on the laptop):

```
docker run --rm -v advisory-llama:/llama:ro -v <repo>:/repo advisory-et:1.5.1 sh -c "cd /repo && python advisory/eval_advice.py --model /llama/spinquant/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8.pte --tokenizer /llama/spinquant/tokenizer.model"
```

Without a model (works anywhere, no Docker):

```
python advisory/run_advice.py --mode template --case advisory/examples/potato_late_blight_severe_hi.json
python advisory/tests/test_safety.py
python advisory/tests/test_extras.py
```

## Which model file and why

We use `Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8.pte` from `executorch-community/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8-ET` on Hugging Face, pinned to commit `911221e` with SHA-256 checks in `export_llama.py`.

- It is Meta's SpinQuant INT4 checkpoint (4-bit weights in groups of 32, 8-bit dynamic activations, 8-bit embeddings), made for mobile ExecuTorch. It is exported by the ExecuTorch team with XNNPACK and a KV cache, which is the reference setup the mentors accepted.
- Exporting from full-precision weights needs more RAM than our 7.8 GB laptop has free. The pre-quantized checkpoints need much less.
- We picked SpinQuant over QLoRA because its export needs no LoRA adapter settings, so there are fewer things to get wrong. We have not compared the two ourselves yet.
- `export_llama.py export --variant spinquant` (or `qlora`) rebuilds the file from Meta's gated checkpoint with a 1024 token context, using the same export flags. It needs a Hugging Face login that has accepted the Llama 3.2 licence. We have not run it yet.
- Weights are never in the repo (Llama 3.2 licence). Anyone using the file accepts that licence, and the app must say "Built with Llama".

## How the advice is kept grounded

- **Grounded prompting, no fine-tuning (Phase 1).** For each case `knowledge.py` picks a few KB facts (signs, two IPM steps, up to two chemicals with dose and waiting period, one safety line). Llama only sees those facts and is told to rewrite them for a farmer, in 120 words or less (80 for Hindi), with no new chemicals, doses or numbers. Severe cases must end with the KVK and Kisan Call Centre line.
- **Uncertain cases never go to Llama.** If `uncertain` is true, or the confidence is below the threshold in `configs/thresholds.json`, the app shows the template: no diagnosis, a retake tip and the referral. In our first test Llama answered every uncertain case with "The crop is wheat. The problem is pest infestation."
- **Safety check on every answer** (`safety.py`): no chemical name outside the case facts (a list of about 150 pesticide names in English and Hindi, plus name-ending patterns), no number outside the facts, no number and unit pair (such as "4 kg") outside the facts, no dose written in words, no crop or problem name outside the facts, a referral where needed, the right script for the language, not cut off, not too long. If any check fails, the farmer gets the template instead.
- **Phase 2 plan: LoRA fine-tune.** Fine-tuning is not possible on our CPU-only laptop. The plan is a LoRA fine-tune on a few thousand curated question and answer pairs written from ICAR, TNAU and state university material, in English and Hindi, checked by a person. The same safety checks would stay in place.

## Memory-aware mode

`memory.choose_mode(available_mb)` returns `llm` when at least 2544 MB is free, otherwise `template`. That is the peak resident memory we measured for the whole runner process with this .pte (2022 to 2032 MB on the x86 laptop) plus a 512 MB margin. The number must be measured again on the phone.

## SMS referral and speech text

- `referral.build_sms(case)` gives a text of 160 characters or less for severe or uncertain cases, with crop, problem, severity, date and a blank for the village. English is plain ASCII and fits in one SMS. Hindi needs Unicode SMS, so it goes as 2 or 3 parts. SMS works without mobile data.
  - `KVK help: tomato late blight, severe 45%. Date 21-11-2026, village ______. Seen by offline crop app. Please advise.`
  - `KVK सहायता: टमाटर, पछेती झुलसा, गंभीर 45%। तारीख 21-11-2026, गांव ______। कृपया सलाह दें।`
- `speech.to_speech(text, lang)` removes list markers and symbols, spells out units and percent, reads the helpline digit by digit and ends each Hindi sentence with a danda, for Android's offline text-to-speech.

## Known limits

- **Laptop numbers are x86, not Arm.** All timings so far come from an Intel i5-1135G7 laptop, inside a Linux container, often sharing the CPU with vision training. They show the pipeline works, not how fast it is on a phone.
- **The first forward call is slow** (about 77 s on the laptop). The runner does it once at load time and reports it separately.
- **Hindi is slower and weaker.** Hindi text takes about three times as many tokens as English, so the prompt is longer and time to first token is higher. The 1B model's Hindi is also less reliable, so more Hindi answers fall back to the template.
- **All Hindi KB text was written by us** and still needs checking by a Hindi speaker (`hindi_reviewed: false`).
- **The safety lists are not complete.** A chemical with a name that is not in our list and does not match the name endings would get through. The number check is strict, so a wrong dose would still be caught.
- **Leaf mold has no chemical**, because we found no Indian dose. The app says to ask the KVK.
