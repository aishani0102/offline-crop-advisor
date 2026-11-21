# Advisory evaluation

Run on 2026-11-21. Script: `advisory/eval_advice.py`. Raw output: `docs/results/advisory_eval_partial_raw.jsonl`.

- Model: `Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8.pte (executorch-community build)`
- Machine: x86_64 Linux container (Docker Desktop, 3.7 GB VM) on Intel i5-1135G7 Windows laptop
- **These timings are from an x86 laptop CPU, not from an Arm phone.** They only show the pipeline works end to end. Phone numbers will be different.
- Note on load: PARTIAL RUN, stopped after 32 of 60 cases (all 30 English cases, 2 Hindi). A vision training job was sharing the CPU for part of the run, so timings are noisy. Load time, warm-up and peak RAM were not saved for this run; see the notes at the end.
- Decoding: greedy, at most 200 new tokens.

## Pass rates

| Measure | Result |
|---|---|
| Cases run with Llama | 32 |
| Raw model output passed every check | 29/32 (91%) |
| Raw output grounded (no chemical, dose or number outside the KB facts) | 32/32 (100%) |
| Referral present where needed (severe or uncertain) | 10/12 (83%) |
| Fallback to the KB template triggered | 3/32 (9%) |
| Final advice shown to the farmer passed every check | 32/32 (100%) |

Why the raw output failed (one case can fail more than one check):

| Check | Cases |
|---|---|
| missing_referral | 2 |
| cut_off | 2 |

- en: raw pass 27/30 (90%)

- hi: raw pass 2/2 (100%)

## Speed and memory (x86 laptop, not a phone)

| Measure | Value |
|---|---|
| Model load time (s) | n/a |
| First forward call, one time warm-up (s) | n/a |
| Prompt tokens | median 279.00, min 185.00, max 639.00 |
| Time to first token (s) | median 2.15, min 0.84, max 74.46 |
| Decode speed (tokens/s) | median 7.64, min 2.73, max 14.27 |
| New tokens | median 78.50, min 36.00, max 200.00 |
| Generation time per case (s) | median 12.51, min 4.10, max 124.74 |
| Peak RAM of the process (MB) | n/a |
| en: time to first token (s) | median 2.00, min 0.84, max 21.28 |
| en: decode speed (tokens/s) | median 8.06, min 3.56, max 14.27 |
| hi: time to first token (s) | median 40.66, min 6.85, max 74.46 |
| hi: decode speed (tokens/s) | median 4.50, min 2.73, max 6.26 |

## Sample outputs

### potato_early_blight, mild, en

Checks failed: none. Shown to farmer: model output.

Model output:

```
Here is the rewritten advice:

You have a crop of potatoes. The early blight, a fungal leaf disease, is affecting them. It's worse in dry, warm weather with rain now and then. Small dark spots first appear on the older, lower leaves. Pick off and destroy the spotted lower leaves and keep watching the crop every week. Plant only disease-free seed tubers. Collect and destroy infected plant debris.
```

### potato_early_blight, severe, en

Checks failed: missing_referral. Shown to farmer: KB template (fallback).

Model output:

```
Here is the rewritten advice:

Potato: early blight, severe. 

- Small dark spots first appear on the older, lower leaves.
- Much of the leaf area is affected.
```

Shown instead:

```
Potato: early blight, severe (about 45% of the leaf).
A fungal leaf disease of potato, found in both hills and plains. It is worse in dry, warm weather with rain now and then, and in weak or poorly manured crops.
Much of the leaf area is affected. Spray soon and get advice from your KVK on the next steps.
What to do:
- Plant only disease-free seed tubers.
- Collect and destroy infected plant debris. Spores left in the soil start the next infection.
- Give the crop balanced manure and fertiliser. Weak crops get this disease more.
If you need to spray, use one of these:
- Mancozeb 75% WP: 600 to 800 g in 300 litres of water per acre, do not spray in the last 10 days before harvest
- Chlorothalonil 75% WP: 350 to 500 g in 240 to 320 litres of water per acre, do not spray in the last 10 days before harvest
- Copper oxychloride 50% WP: 1 kg in 300 to 400 litres of water per acre, do not spray in the last 6 days before harvest
Read the label on the pack before you mix anything, and use only the dose on the label or the dose your KVK gives you.
Wear gloves, a face mask and a cap while mixing and spraying. Cover your feet and hands.
Please show the plant to your nearest KVK (Krishi Vigyan Kendra) or call the Kisan Call Centre on 1800-180-1551 (free call).
```

### potato_early_blight, mild, hi

Checks failed: none. Shown to farmer: model output.

Model output:

```
आलू की पत्तियों का फफूंद रोग
आलू की पत्तियों का फफूंद रोग होता है, जो पहाड़ और मैदान दोनों में होता है। यह सूखे, गर्म मौसम में बीच-बीच की बारिश में और कमज़ोर या कम खाद वाली फसल में ज़्यादा फैलता है। पहले पुरानी, नीचे की पत्तियों पर छोटे काले धब्बे दिखते हैं। सिर्फ़ कुछ धब्बे हैं। धब्बे वाली नीचे की पत्तियां तोड़ कर नष्ट करें और हर हफ़्ते फसल देखते रहें।
```

### tomato_leaf_mold, moderate, uncertain, en

Checks failed: none. Shown to farmer: model output.

Model output:

```
The crop is wheat. The problem is pest infestation. Please show the plant to your nearest KVK (Krishi Vigyan Kendra) or call the Kisan Call Centre on 1800-180-1551 (free call).
```

## Notes from this partial run (read before using any number above)

- **This run is not finished.** It stopped at 32 of 60 cases when we paused work. Hindi has only 2 cases, so the Hindi pass rate means nothing yet.
- **Peak RAM.** Not saved in this run. In two separate single-case runs of `run_advice.py` on the same container the peak resident memory of the whole process was 2022.5 MB and 2022.4 MB. `memory.py` uses 2032 MB as the peak.
- **Warm-up.** The very first forward call after loading took about 77 s in a benchmark (one 64 token prefill). After that, a 400 token prefill took 2.7 s (146 tokens/s, 4 threads) and decode ran at 9 to 17 tokens/s. The runner now does this warm-up once at load time and reports it separately.
- **Long time to first token for Hindi.** Hindi prompts are longer (about 640 tokens against about 280 for English) and the CPU was shared with a training job, so these numbers are noisy.
- **A problem the checks did not catch.** All 4 English uncertain cases gave the same wrong text: "The crop is wheat. The problem is pest infestation.", followed by the referral. It passed every check because it names no chemical and no number. Wrong crop or condition names are not checked yet. Fix planned: either use the template for uncertain cases, or add a check that the output names only the crop and condition from the case.
- **Chatty first line.** Most raw outputs start with "Here is the rewritten advice:". `clean_output` in `prompt.py` removes it before the safety check, so the farmer does not see it.
- **Some outputs add vague labels** such as "a mild disease" or say the leaf "is affected" without the main step. They are grounded but not always the most useful facts. More prompt work is needed.
