# Canonical orb colours — Kimarite (B12 and later)

**Never reverse Power and Spirit.** The approved presentation convention is:

| Stat | Orb | Card model field |
| --- | --- | --- |
| Power | 🟣 purple | `Card.power` |
| Technique | 🟢 green | `Card.technique` |
| Spirit | 🟠 orange | `Card.spirit` |

The engine's `Card(id, name, power, technique, spirit, ...)` tuple order **does not change**. Colours are presentation metadata only. Always render using `kimarite.models.format_card_orbs(card)`, which is protected by `tests/test_orb_colours.py`. Never manually infer the orb colours from a remembered table.

## Corrected top-ten prepared Tachiai cards (B12 7,080-bout baseline)

The following percentages and sample sizes are from the 7,080 completed bouts in [B12 GitHub Actions run 41542521604](https://github.com/thomasw326/kimarite/actions/runs/41542521604/artifacts/13186708111), aggregating `card_assignments.csv` where `role == prepared_tachiai`. Win rates are observational and do not isolate the effect of the card.

| Rank | Card | Approved printed orbs | Won / bouts prepared | Win rate |
| ---: | --- | --- | ---: | ---: |
| 1 | Explosive Step — Fumikomi | 🟠🟠🟠 | 115 / 164 | 70.1% |
| 2 | Get Underneath | 🟣🟢 | 175 / 260 | 67.3% |
| 3 | Give Ground | 🟢🟢🟠 | 45 / 68 | 66.2% |
| 4 | Henka | 🟢🟢🟢🟢 | 157 / 242 | 64.9% |
| 5 | Sidestep | 🟢🟢🟢 | 116 / 182 | 63.7% |
| 6 | Stare Down | 🟣🟢🟠 | 360 / 576 | 62.5% |
| 7 | Spin Away | 🟢🟠🟠 | 23 / 38 | 60.5% |
| 8 | Chiri-chozu | 🟣🟢🟢🟢🟠 | 83 / 138 | 60.1% |
| 9 | Hakkeyoi! | 🟠🟠🟠 | 119 / 204 | 58.3% |
| 10 | Shiko Stomp | 🟣🟠🟠🟠🟠 | 123 / 214 | 57.5% |

**Note:** Only print displayed orbs; Tachiai effects must be separately derived from `src/kimarite/tachiai_effects.py` and not inferred from a card's Exchange effect. The original card counts, calculations and recorded bout results are unchanged.
