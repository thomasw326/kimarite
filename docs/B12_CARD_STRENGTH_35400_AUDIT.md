# B12 card-strength 35,400-bout audit

This is an observational test on the same B12 rules and the same 60 wrestler framework decks as the Utchari -4 / Tsukiotoshi +2 build. **No balance or deck changes.**

## Design
- 60 frameworks and 15 existing AI style profiles (4 each); 1,770 unordered matchups; both sides mirrored.
- 5 distinct seeded repetitions per matchup per deck mode. Modes `base28` and `max40`: 1,770 × 2 × 5 × 2 = **35,400 total bouts** (17,700 per deck size).
- Master seed 20261102, deterministic existing per-pair/per-framework repetition seed derivation, identical original deck blob hash `92618ce1d60ec8591381f045547dbac3f8b056f3`.
- Runner `scripts/b12_60_big_test.py`, report `scripts/b12_60_report.py`; 12 shards per deck mode, no repeated seed within a pairing.

## Mandatory report outputs
- `card_played_vs_unplayed.csv`: per-card per-framework and per-mode bout win rates when played vs unplayed, including any-origin play.
- `card_assignments.csv`: win rates when Tachiai-prepared vs designated top-of-deck, separate.
- `card_inclusion.csv`: inclusion win rates by one/two copies.
- `card_origin_play_rates.csv`: deck-origin Kimarite played versus starting-origin, where observable.
- `starting_kimarite_performance.csv`, `kimarite_finishes_by_origin.csv`, `victory_methods.csv`: starting Kimarite win rates, actual finishing instance provenance, all win sources.
- `card_immediate_contributions.csv`, `temporary_outcomes.csv`: Push, Momentum, Power, cards and Plays deltas, temporary outcomes.
- `hand_exposure.csv`, `game_length.csv`, `tachiai_advantages.csv`, `matchup_results.csv`, `framework_results.csv`: exposure, timing, side/matchup effects.
- `summary.json`: coverage, all bout totals and errors; fail on missing/duplicate/non-mirrored records.

## Analysis approach after run
Priority: weakest cards overall, particularly new one-effect cards; weak/strong Kimarite for starting, deck played and actual finishing share; prepared vs Exchange usefulness; check 28/40 changes before wrestler redesign. Report denominators and avoid over-reading small samples or interpreting observational played-versus-unplayed association as causal. Exact per-draw-event counts and delayed effect attribution are **not** fully tracked by the current runner; identify these gaps rather than invent metrics.

## Regression
Correct stale historical assertions for the already-approved Utchari -4 and Tsukiotoshi +2 thresholds. These changes only align tests with current gameplay.
