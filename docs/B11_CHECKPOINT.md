# B11 — Human Playtest Balance & Interface Checkpoint

**Status:** B11 playtest baseline, preserved from `feature/b10-human-ui-session` at commit `25d55f475acea8061c84a087b1ed74579c5a6d65` (25 October 2026). This checkpoint captures user-approved experimental card changes and the playable human UI. It is **not** a new claim that all statistical balancing or full CI is complete.

## Provenance and scope

- **Prior frozen B10 baseline:** `311dec7de8a0e3ef30365eeb8f0b8cd832912a4f`. Preserve that commit and do not rewrite or silently replace it.
- **B11 source:** `feature/b10-human-ui-session`, PR #48, at `25d55f4`.
- **B11 checkpoint branch:** `release/b11-playtest`; do not merge it automatically into `main`.
- B11 includes the Human vs AI web app, five rounds of three tournament bouts, card information/inspector, and zone-only active effects.

## User-approved B11 balance changes

1. **Power Water Cantrip** (planned player-facing name **Power Water Refresh**): Recover **up to 3** discarded cards (previously 1), gain +1 Play, draw 1. The UI currently chooses an initial discard target; remaining recovery selects newest remaining discards automatically. Generated card remains exhausted after use. Power Water itself still generates six copies.
2. **Morozashi — Double Inside Grip:** Still requires at least one existing Grip, establishes the other side when needed, and grants **+1 Push and +1 Momentum** if its Temporary survives to next turn (previously +1 Push only). Affinities not changed.
3. **Harite — Open-Hand Strike:** At Exchange and prepared Tachiai, opponent discards one **random** hand card (if available), loses 1 Power and mills up to 2 draw-pile cards, unless protected. Replaces own +1 Power / opponent −1 Power. Random choice is reproducible based on current bout state.
4. **Shiko Stomp:** In Exchange, adds +1 Play to refund its Play cost. Existing single-use negative-effect protection remains; prepared Tachiai continues to establish protection without extra Play.

## B11 user-interface changes carried forward

- Five-round, 15-bout management tournament with nine-card deal for every three bouts; no repeat opponents; results tracked by opponent style, turn and finishing method.
- Visible active/delayed effects only in Temporary Zone and victory conditions only in Kimarite Zone, for both players; hand/selection inspector still retains full descriptions.
- Zone-effect summaries simplify Push shields and show surviving/disrupted delayed effects.
- Tournament result history currently uses browser session storage and does not backfill older bouts.
- The new **72-entry display-name catalogue** exists at `docs/B10_DISPLAY_NAME_CATALOGUE_DRAFT.md` with approved decisions and remaining straightforward proposals; naming was **not rolled out to all UI labels** as of this checkpoint.

## Open B11 design and QA follow-ups

- **Hatakikomi** remains Momentum ≤ −2 and Power ≥ 6, without Position or Unstable requirement. Earlier Position ≥ 0 + Power ≥ 5 version exists in historical sheets; a later HAT-C3 variant was intentionally approved. **No new Hatakikomi change authorized.**
- **Kachiage** is implemented; its source label in one protection call says Nodowa. Review without accidentally changing B11 rules.
- **Morozashi affinity:** Investigate why it appears in Oshi-oriented decks; no affinity edits approved yet.
- **Power Water** optional enhancement: let a human explicitly choose all recovered cards rather than only the first.
- **UI**: Sidestep predicted survival/disruption outcomes and Kimarite tracking could be clearer.
- **Verification:** UI smoke on source commit `25d55f4` completed successfully (workflow run `40144998627`). Full tests workflow `40144998634` was still in progress when this checkpoint was prepared. Check full suite and targeted card tests before release/merge; do not claim clean full CI.
- **B10 main is immutable**; any further B11 balance tuning should proceed with explicit changes, tests, and a documented follow-up commit.

This checkpoint records the end-of-session state so work can resume without losing the approved changes.
