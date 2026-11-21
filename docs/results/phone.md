# Phone results

Phone: Redmi 12 5G (Snapdragon 4 Gen 2, arm64-v8a, Android 15, about 1.8 to 2.3 GB free RAM).
Runtime: executorch-android 1.5.1 from Maven, the same version the .pte files were exported with.
All numbers come from `timings.log`, which the app writes to its files folder
(`/sdcard/Android/data/app.cropadvisor/files/timings.log`). Raw logs from 21 Nov 2026 are kept
with the model files, outside the repo.

## Leaf model (mnv3_large_int8.pte, 4.5 MB, bundled in the APK)

| What | Value |
|---|---|
| Classify one photo (resize, crop, forward pass) | 70 to 300 ms, first run after start is the slowest |
| Phone vs PC on the same test images | top 3 matched (checkpoint B); test_015492.jpg gives Septoria leaf spot at 0.885 on the phone |
| Fresh install, nothing pushed | classifies, model loaded from the APK assets |

## Language model (Llama 3.2 1B Instruct SpinQuant INT4, 1.1 GB, pushed with adb)

| What | Short test prompt (40 tokens) | Grounded advice prompt (KB facts) |
|---|---|---|
| Load | 2.4 to 5.1 s | 5.7 to 7.4 s |
| Time to first token | 1.3 to 1.9 s | 7.9 to 8.0 s |
| Decode speed | 9.8 to 14.2 tokens/s | about 12 tokens/s (95 tokens in 8.0 s) |
| Peak RSS of the app | 1559 MB | 1511 to 1538 MB |

Why time to first token is so different: prefill runs at about 30 tokens/s on this phone. The
short test prompt is 40 tokens, so it takes about 1.3 s. The grounded prompt carries the system
rules plus the KB facts for the case (about 230 tokens), so prefill alone takes about 7.5 s.

## Free RAM gate

The app only starts Llama when the phone reports at least **1900 MB** free (`Advisor.LLAMA_NEEDS_MB`).
The advisory code on the PC uses 2544 MB (2032 MB peak measured on the laptop plus 512 MB margin).
On the phone the whole app peaked at 1559 MB with Llama loaded, so 1900 MB leaves about 340 MB
margin. With the old 2544 MB gate Llama never ran on this phone (free RAM was 2117 to 2274 MB).
Below the gate the app shows the template advice, which uses the same KB facts.

## Differences from the Python advisory code

- **KVK line retry.** If the Llama answer fails the safety check only because the KVK or Kisan
  Call Centre line is missing, the app adds the fixed KB referral sentence and checks again. In the
  first phone run Llama dropped that line and the answer fell back to the template; with the retry
  the same answer passed. The Python code (`advisory/safety.py`) does not do this retry.
- **Languages.** The app offers English, Hindi, Bengali, Marathi, Tamil and Telugu. Llama only
  writes English and Hindi. Bengali, Marathi, Tamil and Telugu always get the translated template
  from `assets/kb_<lang>.json`. Those files are marked `"reviewed": false` and only hold the text
  the phone template shows now; anything missing falls back to English. Hindi comes from `kb.json`,
  where `hindi_reviewed` is still false.
