# B11 player-controlled Tachiai — approved implementation specification

Status: **design approved, implementation pending**. Do not represent this mode as playable until server and client both support it. This supersedes the prior player-facing mandatory Kimarite/prepared/top-deck arrangement; retain that arrangement as a selectable **Classic opening** mode for comparison.

## UI
- Opening mode dropdown: **Player-controlled Tachiai (default)** / **Classic opening (legacy)**. This should work in both standalone bouts and the 15-bout tournament.
- Tournament: player allocates three distinct cards per bout from the nine-card deal, retaining current three-bout grouping. Those cards are the **three offered opening cards** for that bout. They are no longer forcibly interpreted as one Kimarite, one prepared card and one top-deck card in player-controlled mode. No card goes on top of the draw pile because of opening selection.
- At bout opening, **before any Tachiai is resolved**, show the three selected cards. For each, player chooses **Commit to Tachiai** or **Keep in hand**. Allow zero, one, two or three commitments. Provide clear before-confirm summary.
- Committed cards each contribute their printed Power/Technique/Spirit orbs and any eligible Tachiai effect. Uncommitted cards remain in the player's initial Exchange hand and do not contribute Tachiai orbs or trigger Tachiai effects. A committed Kimarite card must have a defined destination consistent with the normal rules; do not silently auto-place one in Kimarite Zone.
- The human has **no mandatory starting Kimarite** in this mode. No mandatory top-deck card. For the player's starting stats/orb formula, retain established base-stat rules and make a deliberate test of the three-card orb calculation.
- Human Oshi/Tsuki consecutive reveal chain: preserve the currently verified Tachiai effect, including stopping after a non-Oshi/Tsuki revealed card that still contributes orbs, but review its draw pile interaction with no forced top card.
- AI setup unchanged: existing automatic starting Kimarite, prepared Tachiai and top-of-deck placement, AI opening stats and effects; AI commits its cards automatically.

## Engine/API implementation requirements
- Currently `new_b10_session` builds two `FighterState`s, computes `compare_tachiai`, applies power and `resolve_prepared_tachiai`, then advances AI **synchronously before returning a session**. Introduce a proper pre-Tachiai state or pending opening selection; do not run AI turns until opening is committed and Tachiai resolves.
- Separate human and opponent opening logic, including session serialization/recovery, public snapshot, available commands and secure hand/draw pile handling.
- The current `_fighter` validates a required starting Kimarite and prepared/top slots; implement player-controlled allocation independently while leaving Classic unchanged.
- Ensure opening card ownership, draw/remove/discard/hand destinations and absence of duplicate card instances are exact.
- Keep full three-card allocation recorded separately for future Draft Mode win-to-duplicate / loss-to-remove consequences, regardless of which cards were actually committed.
- Cover 0/1/2/3 committed cards, zero Kimarite among selected cards, a selected Kimarite retained in hand, prepared Oshi reveal chain, and the untouched AI Tachiai behaviour; test seeded recovery/replay.
- Ensure player-facing logs hide opponent's unrevealed drawn cards in production (debug view may retain full detail).

## Follow-on
- Implement **Draft Mode** only after player-controlled Tachiai is working: 30 unique card draft, initial 3 mandatory Kimarite, maximum 8 Kimarite in initial deck; winning bout duplicates one of the allocated 3 (max 2 copies, total 40 cards), losing bout removes one of the allocated 3.
- Fixed AI 28-card unique base + 12 ordered affinity-reviewed duplicates, difficulty = wins - losses with independently sampled integer offset in [-2,2], deck maximum 40; original seven-step priority stat pattern applied in both directions, each stat floor 0.

No changes to the frozen B10 baseline. Implement and test on B11 branch before offering as default in the playable UI.
