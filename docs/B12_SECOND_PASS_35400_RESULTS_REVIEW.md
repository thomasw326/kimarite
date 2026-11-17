# B12 second-pass 35,400-bout card review — 7 November 2026

**Status:** Results reviewed; **no further card changes, deck edits, main-branch merge, or release-lock updates approved by this review**.

## Provenance and valid comparison

- Current [successful run #42322655349](https://github.com/thomasw326/kimarite/actions/runs/42322655349), commit `884fef398f73db18ff06161effbc83f5238ac003`, source deck SHA-256 `3ca76ade98212a5b0563fdc76e71fcb3d103e01484639b2de4eade5760388f22`.
- Prior first-pass rebalance [successful run #41914709610](https://github.com/thomasw326/kimarite/actions/runs/41914709610) is the primary *before the second-pass approvals* comparator. Intermediate [run #42272155018](https://github.com/thomasw326/kimarite/actions/runs/42272155018) already includes Get Underneath's Exhausted penalty and Nekodamashi's penalty removal; do **not** treat that intermediate run as a clean no-change control for those two.
- 60 identical deck definitions, unchanged AI styles/mapping, seed 20261102, 1,770 unordered pairings × two directions × five repetitions × two deck modes. Completed exactly **17,700 base28 + 17,700 max40 = 35,400 bouts**, zero reported simulation errors, 60 frameworks per mode. Every bout contributes two fighter observations to per-card role cohorts.
- These are **simultaneous card changes** in a round-robin. Win-rate shifts for a card's owning decks are *associations*, not estimated individual card causal effects. A card's played/not played cohorts are determined by game length, AI choices and state; the inclusion/exclusion cohort compares *different wrestler decks*. No random-assignment, opponent-controlled, card-isolation inference is warranted.
- Role cohorts are calculated **among decks that contain the card**, except included/excluded. All percentages below aggregate both modes with the relevant denominators; the mode-specific differences are given separately. No exact trigger counts for exhausted Get Underneath nor delayed ritual draws are recorded.

## Updated cards: outcomes (both modes)

| Card | Including decks: latest win % | Change vs first pass (pp) | Exchange played / not played % | Tachiai selected / not selected % | Top-deck selected / not selected % |
| --- | ---: | ---: | ---: | ---: | ---: |
| Get Underneath | 54.05 | +0.30 | 58.94 / 51.48 | 57.29 / 53.91 | 57.77 / 53.88 |
| Nekodamashi | 49.72 | +0.46 | 46.37 / 51.51 | 52.79 / 49.57 | 47.40 / 49.82 |
| Denshamichi | 54.11 | -0.05 | 61.28 / 50.08 | 49.59 / 54.32 | 61.20 / 53.77 |
| Spin Away | 54.66 | -0.27 | 60.85 / 51.75 | 46.94 / 54.95 | 58.85 / 54.52 |
| Explosive Step — Fumikomi | 55.14 | +0.66 | 53.96 / 55.78 | 50.72 / 55.36 | 52.25 / 55.28 |
| Chiri-chozu | 49.55 | +0.75 | 47.65 / 49.96 | 54.66 / 49.33 | 49.62 / 49.55 |
| Salt Throw | 49.13 | -0.06 | 47.84 / 49.59 | 55.79 / 48.87 | 43.65 / 49.37 |
| Shikiri | 46.83 | +0.64 | 48.34 / 46.24 | 53.82 / 46.48 | 42.59 / 47.01 |
| Sheer Grit (unchanged) | 59.59 | +0.48 | 62.60 / 58.26 | 53.95 / 59.78 | 54.44 / 59.79 |

**Role sample sizes:** prepared Tachiai selected, in row order above: 1,248, 1,578, 1,468, 294, 828, 644, 2,400, 1,282, 228. Exchange played: 10,945, 11,920, 11,461, 2,641, 6,247, 2,747, 16,293, 7,596, 2,171. Card-included fighter observations: 31,860, 34,220, 31,860, 8,260, 17,700, 15,340, 62,540, 27,140, 7,080. All role sample denominators are available in the run's `card_role_comparisons.csv` (including zero-denominator protection).

## Each update: 28-card and 40-card mode checks

Deck-inclusion win-rate difference from the **first-pass** run (latest minus first-pass; percentage points):

| Card | base28 | max40 | Interpretation |
| --- | ---: | ---: | --- |
| Get Underneath | +0.05 | +0.55 | Exhaustion penalty does not visibly suppress its strong, positive played-cohort association; trigger-specific measurement is missing |
| Nekodamashi | +0.41 | +0.50 | Small improvement consistent with removing a downside, but still a negative played/not-played association |
| Denshamichi | -0.16 | +0.06 | Essentially stable owning-deck strength despite swapped opponent finisher |
| Spin Away | -0.36 | -0.17 | Small decline; only 7 owning frameworks |
| Explosive Step | +0.36 | +0.95 | Clear direct Push increase, modest owning-deck benefit (especially max40) |
| Chiri-chozu | +0.94 | +0.56 | Modest improvement despite fewer exchange plays; permanent delayed-draw value not attributed |
| Salt Throw | +0.03 | -0.14 | Far more deck recycling without meaningful owning-deck uplift |
| Shikiri | +0.81 | +0.47 | Extra Play has useful impact, though its decks still underperform the population |
| Sheer Grit (unchanged) | +0.11 | +0.85 | Still powerful in 6 specific decks; cannot justify an automatic nerf |

### Resource / behaviour sanity checks

- **Shikiri:** observed 2,918 + 2,810 card plays in first pass (base28 + max40), versus **4,048 + 4,024** now. Exactly **8,072 extra Plays net** are recorded on current Shikiri play events versus zero in first pass. Source confirms +1 Play **only in Exchange**, while Tachiai enters permanent Temporary without +Play. More aggressive play selection is compatible with this buff; not proof that each additional play created an extra turn-winning card.
- **Explosive Step — Fumikomi:** current measured immediate Push **2,645 base28 + 3,269 max40 = 5,914**, versus **1,904 + 2,234 = 4,138** in first pass. Plays changed from **6,742 to 7,003** across modes. Measured Push per play rose approximately **0.614 → 0.844**; own mill-2 cost persists. Exchange played/not-played separation improved but remains negative in combined cohorts, particularly in max40. Keep an eye on the 15 owning aggressive frameworks rather than declaring the card universally efficient.
- **Salt Throw:** measured own draw-pile depletion is **-47,027 base28 / -37,230 max40**, versus **-30,459 / -24,668** first pass. Negative value denotes net draw-pile replenishment; increase in magnitude is approximately **53%**. Yet its owning decks' win rate is basically flat. Selected Tachiai is associated with much better outcomes than not selected, while designated top-deck selection fares substantially worse; selection bias and delayed Temporary value prevent simplistic role ranking.
- **Chiri-chozu:** current card plays **1,602 + 1,196 = 2,798** vs **2,017 + 1,671 = 3,688** first pass, ~24% fewer. Lower orb count does not imply that fewer plays or positive Tachiai association constitute failure: the once/turn ritual draw is delayed and omitted from direct contribution attribution.
- **Get Underneath:** +1 Push/+1 Momentum remain large direct effects; current played/not-played **58.94% / 51.48%**; positive within-framework played association in **24/27 base28** and **26/27 max40** owning frameworks. The added 7+ discard Unstable penalty is not separately logged as a rate or stratified by threshold, so cannot be declared ineffective just from aggregate results.
- **Nekodamashi:** disrupted Temporary events in the two modes total **1,322**, down from **1,581** first pass; this may reflect bout-state changes, not an underlying protection success rate. Own-deck aggregate increased +0.46 pp. Its Tachiai-selected cohort is positive but its Exchange played cohort is negative. Do not reflexively nerf or buff from either observational contrast.
- **Denshamichi / Spin Away:** present in **27** and **7** frameworks respectively. Exchange played rates exceed not-played by **11.20 pp** (Denshamichi) and **9.10 pp** (Spin Away); selected Tachiai is *below* not-selected by **4.73 pp** and **8.01 pp**. These role gaps are not causal but suggest Exchange is the more valuable observed use. Swapped disruption-generated opponent finishers are reflected strongly in actual finishes.
- **Sheer Grit:** no change in this pass; 59.59% across only 6 owning decks and 62.60% in played bouts. Stay with approved **retain** decision; this batch provides no clean reason for an immediate nerf.

## Win-condition mix and systemic signals

Across both modes combined, compared to the first-pass run:

| Winning outcome | First pass | Current | Difference |
| --- | ---: | ---: | ---: |
| Generated Okuridashi | 36 | 561 | **+525** |
| Generated Okuritaoshi | 343 | 34 | **-309** |
| Tsukitaoshi (all origins) | 3,220 | 3,386 | +166 |
| Kotenage (all origins) | 1,991 | 1,831 | -160 |
| Power victory | 2,763 | 2,521 | -242 |
| Ringout Oshidashi | 4,463 | 4,520 | +57 |

All Okuridashi and Okuritaoshi finishes are reported as **generated** by `kimarite_finishes_by_origin.csv`. The dramatic change confirms finisher provenance is different after the Denshamichi / Spin Away disruption swap. It does **not** establish that +525 winners are attributable solely to that swap (the pool of bouts changed after other card edits).

Average bout length fell **9.018 → 8.975 turns** base28 and **9.035 → 8.994** max40. Current wrestler win-rate spread remains wide: **28.98–64.24%** in base28, **28.81–67.80%** in max40, so more card-rate comparisons are affected by strong and weak owning frameworks than by a card's intrinsic value.

Selected framework shifts vs first-pass: base28 biggest gain **#42 hand-advantage toolbox +4.75 pp**, then **#9 deep-grip surgeon +3.39**, **#43 Unstable technical combo +3.22**; biggest losses **#2 power attrition -3.56**, **#28 cycling quick-Grip -3.05**. Max40 top gains **#37 heavy-Technique Grappler +4.75**, **#12 Grip-endurance controller +4.58**, **#52 left-hand Grip specialist +3.73**; biggest declines **#8 pure defender -3.73**, **#13 power attrition -3.22**, **#3 Power-pusher -2.88**. Effects are joint and may be relative to altered opponents.

## Review decision / next experimental priority

1. **Retain and continue observation, no approval requested for another numerical card edit yet:** Shikiri, Explosive Step, Chiri-chozu, Salt Throw, Nekodamashi; their direct behaviours match the approved patch and aggregate improvements are not obviously broken.
2. **Investigate Get Underneath with a threshold-stratified replay** (exchange plays at discard counts 0–6 vs 7+, actual Unstable events, downstream Kimarite gifts, and opponent matchup controls) before deciding whether its new penalty is sufficiently punitive. It remains a strong active card.
3. **Monitor the Okuri finisher split**, and ideally isolate the Denshamichi / Spin Away gift swap in a single-variable rerun if generated Okuridashi is changing how often opponents can finish.
4. **No immediate Sheer Grit nerf**; preserve earlier decision.
5. **AI role-selection review** can prioritize Denshamichi, Spin Away, Shikiri and Salt Throw: observed Tachiai / top / Exchange associations are striking but confounded. Do not change AI from observational correlations alone.
6. No update to the 60 deck JSON, card effects, or main until the user approves a further experiment.

Source files: `card_role_comparisons.csv`, `card_immediate_contributions.csv`, `temporary_outcomes.csv`, `kimarite_finishes_by_origin.csv`, `victory_methods.csv`, `framework_results.csv` and `game_length.csv` in the current combined artifact, plus corresponding first-pass artifacts.
