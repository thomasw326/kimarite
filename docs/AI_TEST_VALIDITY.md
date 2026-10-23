# V5.1 TEST VALIDITY NOTICE — 2026-10-11

## Mandatory AI selection policy

For 15-style balance tests, use `kimarite.style_ai_v5.play_style_turn` (tactical survival + explicit style card-preference bonus). Do not use `kimarite.personality_ai.play_personality_turn` (obsolete orb-first selector). The latter may exist for historical V4.5 reproduction only and MUST NOT power new 15-style calibration tests.

## Invalidated benchmarks (archive only; NEVER balance against these)

- V5.1 225-build single round robin: 25,200 bouts, runs 38118523725 and 38120489652.
- V5.1 difficulty −7 21,000-bout mirrored baseline: run 38120199080.
- Derived 225-build rankings, style-by-difficulty correlations, Kimarite conversion numbers, and −7 style rankings from those runs.

These results were generated through `scripts/styles_test.py` calling the obsolete personality-first orb selector. They are historical diagnostics ONLY, not evidence of current style balance or Kimarite power.

## Correct reference

- V5.0 paired-seed 15-style baseline, 4,200 bouts, run 38025928484, commit 865d007a03de1acb71977fce2f257e9fec0b12ae, used `style_round_robin_v5 -> style_simulate_v5 -> style_ai_v5`.
- On 2026-10-11, `scripts/styles_test.py` was changed to route through the V5 style-aware AI for FUTURE runs. This does not repair past artifacts.
- Before trusting new balance outputs, validate the simulation calls the style-aware AI, and clearly label its code revision and test conditions.
