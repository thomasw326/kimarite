# B7 APPROVED STANDARD — 2026-10-13

**This is the authoritative B7 four-style balance baseline**, not the older V5.2/PR17+ snapshot.

- Reference branch: `experiment/b7-uwate-topdeck-10k`
- Validated Actions run: https://github.com/thomasw326/kimarite/actions/runs/38486587409 (10,000 bouts, smoke + 5 shards + aggregate green)
- Four fixed 40-card decks: `data/b7_charger_four_fixed40.json`. Pressure Fighter has **Shove ×3, Tsuppari ×2** (the separate locked Pressure Fighter snapshot in `data/pressure_fighter_draft40_20261012.json` must agree).
- B7 card library: the two `B7 Current 61-Card Pool` tabs in **Kimarite Card Library** and **Kimarite V5.2 — Three-Wrestler 30k Batches**. Both point to this standard.

## Current B7 rules and notable card text

**Duplicate Kimarite rule (global).** Whenever you **play** a Kimarite whose *name* already occurs in **your Kimarite Zone**, gain **+1 Play**. Every later duplicate of that name qualifies again. The first played copy does not. A starting/created copy already in the Zone counts. This is implemented in `src/kimarite/playing.py`, with `tests/test_duplicate_kimarite_canary.py`. It is **not** limited to the current turn.

**Tsuppari (2 Power, 0 Technique, 1 Spirit).** Prepared: shuffle three generated Oshi, three Tsuki and three Shove into the draw pile. Exchange: gain 1 Momentum; if Oshi, Tsuki, Tsuppari or Shove was played earlier this turn, gain 1 Push; gain **+1 Play and draw 1 card**. Do **not** use the experimental no-draw rule.

**Uwate (0 Power, 4 Technique, 0 Spirit).** Prepared: if you win Technique, gain 1 Momentum. Exchange: improve Left Grip, enter Temporary until the start of your next turn; if you have Deep Left Grip after improving, play the top card of your deck **for free**. Current implementation: a top card that is illegal to play stays atop the deck and does not trigger a play; an empty draw pile does not create a play. There is **no look/choose** effect. Do **not** use the intermediate discard-on-play Uwate build.

**Shitate (0 Power, 4 Technique, 0 Spirit).** Prepared: if you win Technique, gain 1 Momentum. Exchange: if Right Grip is Deep, gain 2 Push; otherwise improve Right Grip; enter Temporary until next turn.

**Shove (1 Power, 0 Technique, 0 Spirit).** Exchange: gain 1 Push; if Oshi, Tsuki or Tsuppari was played earlier this turn, draw 1 card (**no discard cost**).

**Harite (2 Power, 0 Technique, 1 Spirit).** Exchange: gain 1 Power; opponent loses 1 Power unless prevented.

**Driving Force (2 Power, 0 Technique, 2 Spirit).** Exchange: choose either draw 1; or if your Power is at least 5, gain 1 Push (and if at least 7, also gain 1 Momentum). Legacy simulator alias `Driving Force — Power Payoff` may appear in historical locked decks.

**Gaburi (1 Power, 2 Technique, 1 Spirit).** Exchange: if no usable Grip, gain 1 flexible Grip; otherwise gain 1 Momentum; enter Temporary. On surviving until the start of your next turn, if your Power is greater than your opponent's, create a Yorikiri in your Kimarite Zone, then discard Gaburi.

Other engine rules, AI, card variants, and deck composition are as implemented in this tested branch; don't replace them from historical documentation.

## Tested cross-style outcomes (10K run)

- Pressure Fighter: **49.10%**
- Fast Grappler: **49.90%**
- The Technician: **51.13%**
- Charger: **49.87%**

Per cross-style pair, 1,000 bouts; all six pairs within 54.1%-45.9%. These are observations, not promises about future builds.

## For future balance work

Start from this branch's rules, use the two current 61-card pool tabs as the print/reference catalog, and preserve historical experimental branches and artifacts as history only. Do not confuse `Playtest Pool 5.0 (PR17+)`, the historical 600-bout branch, or the Tsuppari-no-draw experiments with B7 standard.
