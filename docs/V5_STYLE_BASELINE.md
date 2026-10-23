# V5 style round-robin baseline

This is a measurement pass, **not approval for balance changes**.

## Reproduction

Run the automated `v5-style-probe` workflow on `feature/v5-integration-controller`, or run locally:

```bash
python -m kimarite.style_round_robin_v5 --repetitions 4 --max-turns 30 > style-probe.json
```

The 15-style mirrored probe runs 840 bouts. Save the JSON artifact and report all style win rates, matchup asymmetries, turn lengths and exhaustion outcomes where available. Record the tested commit SHA and card snapshot version when interpreting results. Do not compare rates against the historical pre-sync probe as though the card sets were identical.

## Current gating

- Latest reported full regression suite before this document: [tests #698](https://github.com/thomasw326/kimarite/actions/runs/38025471022), passed.
- **Search keyword:** automatically take the first/topmost card in Draw Pile order matching the requested category; do not present the full deck or a choice dialog.
- This probe's numbers are exploratory and cannot be treated as a verified new balance baseline until its artifact has been inspected.
- Do not change cards, stats, style construction, or balancing rules without designer approval.
- Keep V4.5 unchanged and PR #16 in draft.

## Confirmed baseline — CI run #704

- Workflow: [tests run #704](https://github.com/thomasw326/kimarite/actions/runs/38025630289), source commit `839f1e9996bdbbfcc68060bc0b85a2c26c5a23c6`.
- Artifact: `v5-style-baseline`, 840 mirrored bouts, 4 repetitions, 15 styles, seed 20261009, max 30 turns.
- **840/840 completed, zero unresolved**. There were 52 opening finishes (6.2%); Side A won 425/840 (50.6%), close to an even orientation split.
- Each style played 112 bouts (14 opponents × 8 bouts per pairing). Observed win rates ranged from 38.39% to 58.04%.
- This is a **descriptive baseline**, not permission to tune cards or style builds.

| Style | Wins / 112 | Win rate |
| --- | ---: | ---: |
| Charger | 65 | 58.04% |
| The Specialist | 65 | 58.04% |
| Mawashi Specialist | 61 | 54.46% |
| The Arsenal | 60 | 53.57% |
| Unorthodox Powerhouse | 59 | 52.68% |
| Opportunist | 59 | 52.68% |
| Speed Demon | 58 | 51.79% |
| The Technician | 57 | 50.89% |
| Power Grappler | 56 | 50.00% |
| Heavy Hitter | 55 | 49.11% |
| Fast Grappler | 54 | 48.21% |
| Disruptor | 53 | 47.32% |
| Pressure Fighter | 48 | 42.86% |
| Bulldozer | 47 | 41.96% |
| Mountain | 43 | 38.39% |

### Strongest observed matchup skews (8 bouts per pair)

- Opportunist 8–0 Pressure Fighter
- Charger 8–0 Bulldozer
- The Specialist 7–1 The Technician
- Speed Demon 7–1 The Technician
- The Arsenal 7–1 Mountain
- Opportunist 7–1 Mountain
- Mawashi Specialist 7–1 Mountain
- Power Grappler 7–1 The Technician
- Heavy Hitter 7–1 Power Grappler
- Unorthodox Powerhouse 7–1 Fast Grappler
- The Specialist 7–1 Disruptor
- The Arsenal 7–1 Disruptor

These are small samples per pairing (8), useful for targeted follow-up rather than conclusive strength rankings.

### Most common wins by finish

Oshidashi 121; Katasukashi 95; Kotenage 73; Tsukiotoshi 70; Hatakikomi 62; Abisetaoshi 62; Oshitaoshi 57; Yorikiri 51. All listed finish categories sum to 840.

### Follow-up validation

- Audit Mountain, Bulldozer and Pressure Fighter for repeatable matchups and early losses **without modifying balance**.
- Investigate the 52 opening finishes, particularly The Specialist (16 opening losses), The Technician (15) and The Arsenal (10).
- Extend seed count / independent repetitions before approving any individual match-up adjustments.
- Preserve frozen V4.5. PR #16 remains in draft pending design review.

## Follow-up protocol: paired seeds, 4,200 bouts

A new CI gate on PR #16 runs 20 repetitions × 105 unordered style pairings × 2 seat assignments = **4,200 bouts** (30-turn cap). Each pair of seat assignments shares one base seed. This corrects the earlier seed mismatch between the two legs, but **does not ensure identical card orders for each style**, because styles are independently seeded by seat in the underlying builder. Treat this as better-controlled replication, not a fully counterfactual same-deck test.

Do not mix its win rates with the original 840-bout results as though they were the same experiment: the seeding policy has changed. Preserve the original report and artifact as historical snapshots. New analysis will emphasize completion rate, seat bias, interval uncertainty, matchup sample sizes, and whether the previously identified extremes persist. No automatic balance changes.

## Larger paired-seed replication — CI run #712

**Source:** [GitHub Actions run #712](https://github.com/thomasw326/kimarite/actions/runs/38025928484), code commit `865d007a03de1acb71977fce2f257e9fec0b12ae`, artifact `v5-style-baseline`. Results also appear in the connected **Kimarite Card Library → 5.0 Data** worksheet.

**Protocol:** 20 repetitions, 15 styles, 105 unordered pairings, two reversed seat assignments per repetition = **4,200 bouts**, 560 appearances per style, seed 20261009, 30-turn maximum. Same base seed for each pairing's two seats, not necessarily identical card order.

- 4,200/4,200 completed, zero unresolved.
- Side A victories: 2,131/4,200 = **50.74%**.
- Opening finishes: 221/4,200 = **5.26%**.
- All winning finish counts sum to 4,200.

| Style | Wins | Losses | Win rate | Opening losses | Average bout turns |
| --- | ---: | ---: | ---: | ---: | ---: |
| The Specialist | 326 | 234 | 58.21% | 71 | 5.29 |
| Mawashi Specialist | 324 | 236 | 57.86% | 17 | 6.78 |
| The Technician | 307 | 253 | 54.82% | 54 | 6.47 |
| Speed Demon | 305 | 255 | 54.46% | 0 | 6.02 |
| Power Grappler | 304 | 256 | 54.29% | 20 | 6.33 |
| The Arsenal | 295 | 265 | 52.68% | 38 | 6.69 |
| Charger | 286 | 274 | 51.07% | 0 | 5.89 |
| Unorthodox Powerhouse | 283 | 277 | 50.54% | 15 | 6.88 |
| Disruptor | 283 | 277 | 50.54% | 6 | 6.64 |
| Fast Grappler | 279 | 281 | 49.82% | 0 | 7.32 |
| Bulldozer | 268 | 292 | 47.86% | 0 | 5.63 |
| Opportunist | 255 | 305 | 45.54% | 0 | 7.43 |
| Heavy Hitter | 249 | 311 | 44.46% | 0 | 6.08 |
| Mountain | 223 | 337 | 39.82% | 0 | 6.39 |
| Pressure Fighter | 213 | 347 | 38.04% | 0 | 6.52 |

### Comparison limitations

This run used *five times more bouts* and changed the pair-leg seed policy relative to the older 840-bout baseline. Raw differences must not be described as the effect of a specific rule or card change. The strongest changes in observed style percentages were Opportunist (-7.14 percentage points), Charger (-6.97), Bulldozer (+5.90), Pressure Fighter (-4.82), Heavy Hitter (-4.65), and Power Grappler (+4.29). Individual style standard errors near 50% are approximately 2.1 percentage points across 560 bouts if treated as independent, but matchup and shared-seed structure may enlarge effective uncertainty. Preserve both results, and evaluate further replication/AI-card usage before any balance changes.

### Finish counts (4,200 total)

Oshidashi 657; Katasukashi 421; Kotenage 328; Yorikiri 318; Tsukiotoshi 315; Abisetaoshi 310; Oshitaoshi 294; Shitatenage 257; Hatakikomi 232; Tsuridashi 213; Tottari 207; Hikiotoshi 201; Uwatenage 197; Power 81; Yoritaoshi 49; Tsukidashi 46; Tsukitaoshi 41; Shove 33.

**No balance changes approved or applied.** The source artifact retains the full ordered-matchup win matrix and per-style exchange card-play counts.

## Card-slot win-rate audit — same 4,200-bout protocol

Source: [CI run #720](https://github.com/thomasw326/kimarite/actions/runs/38026729559), source commit `5e9ba76a574b5e4574d91d13804c83b96bc89956`. Card-slot outcome data is in the JSON artifact's `card_slot_outcomes` field and the connected **Kimarite Card Library → 5.0 Data** worksheet beginning at row 114.

For each bout participant, record a single card in **Starting Kimarite**, **Tachiai**, and **Top**, plus every unique card included in the **Shuffled** remainder. The record describes a deck-build inclusion, not a played-card effect. Each of the first three categories accounts for 8,400 participant appearances and 4,200 wins, 4,200 losses. Shuffled cards account for 369,600 card-in-deck appearances across 8,400 participants. For every row, appearances = wins + losses.

Examples of role-dependent outcomes:
- **Headlong Charge**: Tachiai 188/477 (39.4%); top 229/441 (51.9%); shuffled 790/1,466 (53.9%).
- **Stare Down**: Tachiai 154/231 (66.7%); top 116/243 (47.7%).
- **Sidestep**: Tachiai 238/386 (61.7%); top 187/342 (54.7%).
- **Use the Tawara**: Tachiai 136/298 (45.6%); top 183/307 (59.6%).
- **Katasukashi** as starting Kimarite: 216/370 (58.4%).

**Interpretation warning:** These are observational correlations across heterogeneous styles and matchups, not isolated treatment effects. The shuffled slot is heavily confounded by exclusions, differing pools, and style prevalence; do not rank card strength causally from that column. No balance adjustments are applied.
