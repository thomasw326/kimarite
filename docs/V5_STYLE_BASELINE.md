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
