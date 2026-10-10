# V5 current-card synchronization audit

**Source:** `Kimarite Card Library` → `Playtest Print Pool V4.3 — Test`, range A1:M63. The literal current card texts and values are frozen in `data/v5_print_pool_snapshot.json`. Tests in `tests/test_v5_print_pool_sync.py` enforce listed orbs and active/retired status.

This is **a rules-parity effort, not a balance-tuning pass**. The pre-sync 840-bout win rates are historical, not a valid comparison to the new full printed card pool.

## Completed

- All currently printed Power/Technique/Spirit values, including synthetic starting-Kimarite definitions
- Active copy count: one each of Oshi, Tsuki, and Tsuppari; Bad Oshi and Big Tsuki retired
- Full active-pool deck construction and exclusion eligibility; Injury kept as the intentional blank control
- Tachiai Oshi/Tsuki reveal chain; Stare Down's Technique **extra card kept**, not merely one additional card looked at
- Oshi/Tsuki Momentum ≥0 checks; Tsuppari bonus Play and draw; six Power Water Cantrips and their exhaustion
- Salt Throw's seven-discard recycling and persistent Tachiai/Exchange Temporary
- Current Tachiai Get Underneath and Henka triggers; Oshidashi's Spirit-comparison alternative
- Immediate/delayed Tsuri, Yori, Gaburi and Attempt Grip card timing
- Regain Balance, Give Ground, Use the Tawara, Reset to Neutral, Read the Move and Pull core Exchange effect changes
- Current Kimarite orb/threshold revisions and recent printed play-effect changes
- Generated-card recognition in the Big Test reporting output

## Still requires precise behavioral parity work

1. **Uwate:** Look at X = Total Grip, choose a card; when Left Grip is Deep, play it without using a Play. Current old shortcut is not compliant.
2. **Headlong Charge (Tachiai):** Sacrificing a Kimarite must be optional and controllable; the current automated opening assumes sacrifice whenever one is available.
3. **Kimarite searches and player choices:** Get Underneath currently selects the first eligible opposing Kimarite; Use the Tawara similarly uses a deterministic search. Human and AI decisions need explicit selection where the rules grant a choice.
4. **Read the Move and Pull:** Both modes exist, but the automatic/controller choice policy should be reviewed and tested for the intended human interface.
5. **Tottari:** The exact trigger window for an opponent's prevented/reduced Grip attempt needs a dedicated audit and tests.
6. **Sidestep, prevention, Temporary interaction:** Verify complete interactions with the current approved text before using this as the new official balance baseline.

## Balance/testing gate

- Keep all V5 edits in `feature/v5-integration-controller` / draft PR #16.
- Preserve `local/v45-card-sync` unchanged.
- Do not infer balance from seed-matched comparisons until card effects and pool composition are confirmed.
- Show complete balance and matchup results to the designer; **no card/stat/rule balancing changes without explicit approval**.
