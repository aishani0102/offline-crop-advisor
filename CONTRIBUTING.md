# Working on this repo

## Branches

- `main` is the branch we submit from.
- Work happens on a branch per track: `detection` for the vision side and `advisory` for the Llama side. Merge into `main` when a piece works end to end.

## Writing style

This goes for docs, code comments, commit messages and anything on the project website.

- Write the way you would explain it to a teammate. Short sentences, plain words.
- Do not use em dashes. Use a comma, a full stop or brackets instead.
- No emojis in docs, the website or commit messages.
- Commit messages: a short line saying what changed, in the present tense ("Add field-only test split"), then a blank line and a sentence or two on why if it is not obvious.
- Only name tools and libraries we actually use in the project.

## Results

Every number that goes into the report must come from a run we can repeat. Save the script, the config and the output file next to each other under `docs/results/`.
