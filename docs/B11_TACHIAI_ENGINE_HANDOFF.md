# B11 Tachiai development handoff

This document tracks what is genuinely implemented vs pending as of commit 87e6b29.

## Implemented (not yet wired into live bouts)
- `src/kimarite/b11_player_opening.py`: validates three allocated cards against actual deck counts; partitions zero to three selected indices into committed and retained; removes the exact three selected instances from draw pile.
- `src/kimarite/b11_player_tachiai.py`: computes human Tachiai as base Power/Technique/Spirit +1 each + printed orbs of committed cards only. Compares against unchanged AI `prepared_stats`.
- `tests/test_b11_player_opening.py`, `tests/test_b11_player_tachiai.py`: regression cases authored; successful CI execution **not yet verified**.

## Next implementation steps (do not skip)
1. Modify live `new_b10_session` flow to construct pending player-controlled opening without calling `resolve_prepared_tachiai` before player choice; preserve exact legacy construction under Classic mode.
2. Add command to choose 0–3 commits, validate server side, then resume resolution. Never allow other session actions before opening is resolved.
3. Generalize Tachiai effect resolution: AI has one prepared card, human can have 0–3 committed cards; each eligible prepared-card effect applies, including Oshi/Tsuki reveal chains. Avoid double resolving Spirit Push / opening position or recycling committed cards incorrectly.
4. Clarify committed Kimarite destination vs ordinary committed cards, and ensure retained cards are delivered into the normal first-turn hand without accidentally being discarded or drawn twice.
5. Expose API phase and snapshot to client; add actual UI decision screen and dropdown (new default, Classic preserved).
6. Update nine-card tournament assignment to unrestricted three-card groups in new mode while maintaining old one-Kimarite/two-ordinary constraint in Classic mode.
7. Run targeted and full tests plus smoke end-to-end; only then enable and report the playable mode.

Do not claim the new mode is functional or shipped before these are complete. B10 main remains frozen.


## Further engine groundwork (October 26)
- `src/kimarite/b11_tachiai_phase.py`: one-shot `PendingPlayerTachiai` receives a validated subset of allocated slots and records committed/retained card objects, without prematurely advancing a bout. Tests: `tests/test_b11_tachiai_phase.py`.
- `src/kimarite/b11_tachiai_reveals.py`: pure multi-commit Oshi/Tsuki reveal planner, consuming sequential draw pile cards up to and including a non-family stopper for **each** committed reveal card. Tests: `tests/test_b11_tachiai_reveals.py`.
- **Still not live**: pending phase, reveal planner and variable orb comparison are isolated modules. The classic live session, UI, and AI remain unmodified.
- **Open correctness concern**: multiple committed cards require careful extension of `resolve_prepared_tachiai` without repeating one-time Spirit Push, and correct treatment of committed Kimarite/ordinary destinations and first-turn hand. Do not expose mode until tests cover this end-to-end.
