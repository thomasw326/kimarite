# B10 Human vs AI — consolidated development status

**Date:** 2026-10-24  
**Scope:** `feature/b10-human-ui-session`, [PR #48](https://github.com/thomasw326/kimarite/pull/48)  
**Frozen source:** approved B10 main commit `311dec7de8a0e3ef30365eeb8f0b8cd832912a4f`.

## Implemented

- Browser-based Human vs AI session using approved B10 State 3 neutral AI and wrestler/deck baseline.
- 26 approved wrestler selections, plus independently randomized human/opponent selection.
- Player-chosen or automatic opening; randomized player selection uses automatic opening.
- Fixed or fresh random bout seed; resolved wrestler names and seed used for recovery and logs.
- Card inspector with audited card descriptions, orb/timing data, and glossary definitions.
- Numbered card-access and discard choices with readable labels, plus separate inspect actions; hidden opponent hand stays hidden. Pull's post-draw discard option is named.
- Active Temporary zone, visible for both wrestlers, with card descriptions directly in the panel. Basic Grip shields **prevent one incoming Push**, consumed when used or expired on the owner's next turn. Delayed/disrupted effects described in card audit.
- Public discard counts and inspectable discard pile contents for both wrestlers.
- Session recovery attempt after process restart, full bout log copy, end-turn confirmation when plays remain.
- Targeted session, snapshot, choice label, and description tests.

## Known UI limits and next work

1. **Dohyo markers do not move**. Only numeric Position and Momentum reflect the game. Planned: wrestler movement by signed Position, separate Momentum indicator, overflow ring danger, and ring-out animation. Not implemented.
2. **Large choice lists** are cramped on small screens; the discard picker needs a responsive full-width or scrolling list with clear Select/Inspect controls.
3. Continue mobile usability regression and check both focused browser smoke and overall tests.
4. The browser session uses reconstruction rather than persistent server-side saves; recovery may be limited by unhandled errors or differing code versions.

## Boundary

Documentation, UI fixes, and explicit regression tests are appropriate on this branch. Do **not** silently change orb counts, card mechanics, opponent AI, deck composition, or ring-out rules; do **not** merge to main without approval. A passing smoke does not establish balance parity or authorize release.

## Reference files

- `web/index.html`, `web/client.js`, `web/style.css`: UI.
- `src/kimarite/b10_web.py`: HTTP controller and choice labels.
- `src/kimarite/b10_human_session.py`: B10 session and public snapshots.
- `src/kimarite/b10_card_info.py`: displayed rules text (rules engine is authoritative).
- `src/kimarite/rules.py`, `src/kimarite/temporary.py`: gameplay implementation (do not alter under UI polish).
- `tests/test_b10_human_session.py`, `tests/test_b10_web_http.py`, `tests/test_b10_card_info.py`: regressions.

## Related development checkpoints

- [Grip shield UI text](https://github.com/thomasw326/kimarite/commit/e4ce32f2c082bb3d8eccee53be83433875462acf)
- [Pull post-draw discard label fix](https://github.com/thomasw326/kimarite/commit/22312e39890e99fe659f67240458f8c55246ecef)
- [Temporary panel descriptions](https://github.com/thomasw326/kimarite/commit/800cdf0ea234a1769a10ff4a0c97e54a68a5feea)
