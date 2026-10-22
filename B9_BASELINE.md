# B9 locked balance baseline — Technique draw-only (2026-10-22)

## Status
**LOCKED FOR FURTHER BALANCE EXPERIMENTS.** This is a named reference branch, not a merge into the repository default branch. Card and deck changes should branch from this baseline and undergo fresh tests before replacing it.

- Tested source commit: `a48c55418917886a2f64cc055848d632c76a270d` on `experiment/b9-36912-technique-10k-lock`.
- Successful [10,000-bout GitHub Actions run](https://github.com/thomasw326/kimarite/actions/runs/39830316151): **10,000 completed; 0 errors**.
- Previous [2,000-bout reference run](https://github.com/thomasw326/kimarite/actions/runs/39827401557): **2,000 completed; 0 errors**.
- Designed-deck source: `data/b9_wrestler_decks.json`; **15 wrestlers, 40 cards per deck**, unchanged from the tested experiment. Randomized-deck mode OFF.
- Detailed standings and win-method comparison: [Kimarite Card Library](https://docs.google.com/spreadsheets/d/1tDtaDeT9fUMfEEzELqhM-_5iG2Y-r1KoxZOfKqMMUq0/edit).

## Locked Tachiai and Exchange rules

- **Technique:** Draw/keep 2 cards normally; the first Exchange-turn Technique advantage adds **+1 card at +3, +6, +9, +12, ...**. This is draw/keep-only; no separate Technique Momentum bonus.
- **Spirit:** Tachiai Push advantage thresholds **+1, +4, +7, +10, ...** (subject to opposing Power resistance).
- **Power:** Tachiai Push resistance thresholds **+1, +4, +7, +10, ...**.
- **Momentum overflow:** Extra Momentum past its cap **does not convert into Push**. Push overflow retains its own existing resolution rules.
- **Turn priority:** Technique, then Spirit, then Power, then ranking.
- **No changes** to the 15 designed decks or the card effects in this confirmation.

## 10,000-bout standings

| Wrestler | Wins | Losses | Win % |
| --- | ---: | ---: | ---: |
| The Specialist | 836 | 490 | 63.05 |
| The Technician | 772 | 556 | 58.13 |
| Pressure Fighter | 757 | 587 | 56.32 |
| Fast Grappler | 723 | 605 | 54.44 |
| Power Grappler | 713 | 631 | 53.05 |
| Bulldozer | 685 | 659 | 50.97 |
| Opportunist | 656 | 672 | 49.40 |
| Unorthodox Powerhouse | 633 | 703 | 47.38 |
| Charger | 635 | 709 | 47.25 |
| Speed Demon | 625 | 701 | 47.13 |
| Mawashi Specialist | 621 | 707 | 46.76 |
| Disruptor | 607 | 719 | 45.78 |
| Mountain | 596 | 730 | 44.95 |
| Heavy Hitter | 585 | 759 | 43.53 |
| The Arsenal | 556 | 772 | 41.87 |

These are results against all 15 designed decks, not proof of isolated stat or card balance. The 2,000-bout and 10,000-bout samples have different sizes; differences may reflect sampling. Keep this baseline stable while reviewing individual card balance.
