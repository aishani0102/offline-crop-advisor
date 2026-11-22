# Personalised advice

After a confident disease or pest result (leaf found, not healthy), the app asks three
questions on one screen. Every question can be left blank, and Skip goes straight to the advice.

- Rain in the last 3 days: yes / no / not sure
- Crop stage: seedling / growing / flowering or fruiting / near harvest
- Sprayed anything in the last 7 days: yes / no

The month comes from the phone clock and the state from a picker on the home screen (saved).

## What the answers change

The answers never add new agronomy. They only reorder KB text or pick extra lines that are
already in the KB (`general_safety`). The rules are in `facts()` in `Advice.kt`.

| Answer | Change | KB source |
|---|---|---|
| Rain = yes, and the KB description says rain, humidity, wet spells or splash spread it | severity note moves to the top | `entries.<label>.context.rain_raises_risk` (added, set from the description text) |
| Rain = yes, spray advice shown | adds "Do not spray ... just before rain" | `general_safety[3]`, copied to `context.before_rain` |
| Near harvest, spray advice shown | products with the shortest waiting period first, adds the waiting period line | `chemicals[].waiting_days`, `general_safety[6]` copied to `context.harvest_wait` |
| Sprayed in the last 7 days = yes, spray advice shown | adds the label dose line and "do not mix pesticides" | `general_safety[0]` and `[5]`, copied to `context.label_dose` and `context.no_mix` |
| Seedling | steps about the nursery or seed go first | order only |
| Month, state | sent to Llama and (state) added to the referral SMS | no KB content |

Llama (English and Hindi only) gets the answers as a FARM line after the FACTS, marked as
"not a fact". The safety check is unchanged, so an answer that makes the model add a number or
a product still falls back to the template.

`kb.json` in the app now has a top level `context` block and `context.rain_raises_risk` on six
entries. `kb_<lang>.json` have the same `context` lines translated. The copy of `kb.json` in the
app was rewritten with two space indents by the script that added these, the content is unchanged.

## Phone run (21 to 22 Nov 2026)

Tomato Septoria leaf spot, severe, answers rain = yes, near harvest, sprayed = yes, state West Bengal:
- Bengali template: waiting period line, before rain line, label dose and no mix lines all shown,
  with no repeated lines (screenshot `app_screens/personal_bn.png`).
- English Llama: passed the safety check, time to first token 15.6 s (longer prompt), 65 tokens.
  The answer did not mention the waiting period, because Llama only rewrites and may drop lines.
  The template shows it.

## Missing, for a person to fill in

- **Repeat spray interval.** The KB has no "do not repeat before N days" for most products. Only
  `potato_early_blight.chemical_note` says "repeating every 15 to 20 days". With sprayed = yes the
  app can only show the label dose line.
- **Act within N days after rain.** The KB says late blight "spreads very fast" but gives no
  number of days, so the app only moves that note up and does not say "act within 2 days".
- **Month or season.** No KB fact links a month to a disease risk. The month is only passed to Llama.
- **State.** No per state KVK list or phone numbers. The app keeps the national Kisan Call Centre
  line and adds the state to the SMS.
- **Crop stage.** No stage specific steps apart from the nursery and seed steps.
- **Translations.** The `context` lines in `kb_bn/mr/ta/te.json` are not reviewed yet.
