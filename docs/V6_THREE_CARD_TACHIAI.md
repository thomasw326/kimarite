# V6 — Three-Card Tachi-ai Format (Working Implementation)

**Status:** Opt-in foundation; NOT yet a replacement for the B7/V5.2 combat simulator.
**Base:** successful B7/R26 commit c9d3d21c8ccbb7d880fd3265507d56a3ab94ceaa.
**Initial roster:** Pressure Fighter, Fast Grappler, The Technician.

## Approved gameplay interpretation

- Each wrestler receives exactly **three starting cards** for the bout.
- In the tournament, the human assigns nine cards across three bouts. AI may receive a guaranteed Kimarite among its starting three, but it follows the same rules once those three are assigned. Do not assume the player has a guaranteed Kimarite.
- Each side chooses which of its three cards to **commit** to Tachi-ai and which to **retain** for the Exchange.
- Only committed cards provide printed Power, Technique, and Spirit orbs. Retained cards provide no opening orbs or opening effects.
- For initial compatibility, preserve the wrestler's base stats plus the existing +1 baseline to each stat. Do not count an additional automatic starting Kimarite or prepared card.
- **Committed non-Kimarite:** resolve applicable Tachi-ai effects, then exhaust for the remainder of this bout. Their Tachi-ai history is inert and does not enter discard.
- **Committed Kimarite:** count orbs, then enter the active Kimarite Zone; other cards can interact with them. Commitment itself is not a win-condition attempt and does not trigger their Exchange text.
- **Retained cards:** remain in Exchange hand and can be played on that wrestler's Exchange turns.
- **Technique:** current 1/4/7/10 advantage thresholds stay provisionally unchanged. First-turn Technique access adds cards to the retained hand, rather than overwriting it.
- **Initiative:** Spirit first, then Power, Technique, and rank to break ties. This is the game design's stated order, intentionally separate from old B7 code.

## First implementation slice

- `src/kimarite/opening_v6.py` contains the shared three-card assignment and commit/retain decision APIs, atomic two-sided validation, scored opening comparisons, active Kimarite placement, bout-long exhaustion, and V6 initiative.
- `src/kimarite/models.py` contains optional historical Tachi-ai and exhausted card lists, empty in all old B7 simulations.
- `tests/test_v6_opening.py` covers legal and illegal assignments and commitments, orb counts, untouched retained cards, Kimarite interaction zone, and initiative order.

## Next necessary work (NOT yet completed)

1. **Multi-card Tachi-ai effects:** Refactor the legacy single-prepared-card effect resolution into a V6 resolver that applies every committed non-Kimarite's relevant Tachi-ai text after simultaneous decisions. No premature force-out before both sides have resolved.
2. **Exchange integration:** Process Power/Spirit Push, possible Tachi-ai ring-out, Technique first-turn card access, and retained hand with correct order.
3. **Controller and UI:** Pause human play for commitment choice; AI sees its own three cards and submits the same choice structure, not a shortcut opening.
4. **Tournament preparation:** Nine-card player allotment in three three-card hands; provisional AI Kimarite guarantee; no automatic guaranteed human Kimarite.
5. **V6 gameplay smoke and targeted balance:** First prove a legal mirrored bout, then small seed tests, then re-run trio calibration if approved.

## Boundaries

This new module **does not claim a fully playable V6 bout yet**: card-specific Tachi-ai effects, opening Push and victory, and Exchange/controller integration are still pending. The B7 30,000-bout baseline and the separate affinity-exclusion run use the old system and should remain untouched.
