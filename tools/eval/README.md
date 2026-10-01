# Test sets for "who is speaking" (tools/talk_identity.py)

| File | Cases | What |
|---|---|---|
| `../talk_eval_cases.json` | 101 | base set: typical door and room sentences |
| `cases_adversarial.json` | 308 | adversarial: corrections, vocatives, idioms, accents, mixed languages, topics that only mention a role |
| `cases_holdout.json` | 307 | written blind (not looked at while tuning until the first run): 90.6 % before tuning, 97.7 % after |
| `real_manifest.json` | 150 | real recordings of native speakers from [Tatoeba](https://tatoeba.org) (metadata only) |

Run the text check (rules + local LLM, no audio):

    python3 tools/talk_eval.py --cases tools/talk_eval_cases.json tools/eval/cases_adversarial.json tools/eval/cases_holdout.json --text-only

State 2026-10-01: 98.9 % (708/716); the 8 misses are known differences between the cases and the spec (§2c).

**Real recordings:** the audio is **not** in this repository (CC BY 4.0 / CC BY-NC 4.0 by their speakers, sentences
CC BY 2.0 FR). `real_manifest.json` lists each clip with its Tatoeba sentence and audio id, speaker (attribution),
licence and the expected speaker. Fetch the audio from Tatoeba by its audio id for your own test run. End to end
(Whisper + identity) all 150 passed on 2026-09-30.
