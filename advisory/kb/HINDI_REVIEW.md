# Hindi text that still needs a reviewer

None of the Hindi text in `kb.json` has been checked by a Hindi speaker yet. Every entry has `"hindi_reviewed": false`. We wrote this text ourselves, so it can have wrong words, odd phrasing or wrong numbers. It should not be shown in a demo until someone who reads Hindi well has gone through it and the flag is set to `true` for that entry.

## Entries to review

| KB entry | Hindi strings | Chemicals with a Hindi dose line |
|---|---|---|
| potato_early_blight | 19 | 3 |
| potato_late_blight | 20 | 3 |
| potato_healthy | 8 | 0 |
| tomato_early_blight | 18 | 3 |
| tomato_late_blight | 19 | 3 |
| tomato_leaf_miner | 19 | 2 |
| tomato_leaf_mold | 15 | 0 |
| tomato_septoria_leaf_spot | 14 | 1 |
| tomato_yellow_leaf_curl_virus | 19 | 2 |
| tomato_healthy | 8 | 0 |

Shared text outside the entries also needs review: `general_safety.hi` (8 lines), `referral.hi`, `uncertain.hi` and `no_dose_text.hi` (11 strings in all).

## What to check first

1. The dose lines (`chemicals[].dose.hi`) and chemical names (`chemicals[].name_hi`). The numbers, units (g, kg, ml, litre, acre) and the days before harvest must match the English line exactly. These 17 dose lines and 17 names matter most because a mistake here is a wrong dose.
2. The referral and helpline text (`call_kvk.hi`, `referral.hi`, `uncertain.hi`). The KVK name and the number 1800-180-1551 must be correct.
3. The severity lines and the safety lines (gloves, mask, label).
4. The rest (description, signs, what to do) for plain, simple words a farmer would use.

## How to mark an entry as reviewed

The reviewer reads the Hindi next to the English for one entry, fixes the Hindi in `kb.json`, and then sets `"hindi_reviewed": true` for that entry only. Please add the reviewer's name and the date to the commit message.
