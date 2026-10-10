## Current verification checkpoint (October 9, 2026)

- **CI green:** test run #672 passed after deferred human-owned search support; subsequent run #676 passed after the Sidestep Temporary lock cleanup and its regression test.
- **Sidestep regression repaired:** when the Temporary is disrupted, Side-by-Side is cleared and future Push is no longer indefinitely suppressed.
- **New baseline trigger:** the V5 style probe workflow now runs when core effects, Temporary, Tachiai, turn, AI, model, or print-pool files change; its results must be evaluated independently of regression success.
- The numbered 5-item list above is the original audit backlog, not the current outstanding checklist. Current unresolved items are independent validation of the baseline probe and any behavioral issues it exposes; card/stat balancing still requires designer approval.

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
- Uwate now looks at cards equal to total Grip, draws a choice normally or plays a legal choice free when Deep Left Grip; human selections prompt and roll back safely
- Generated Power Water Cantrips exhaust instead of moving to Discard; Stare Down grants an extra kept card
- Printed Oshi-family duplicate copies removed and deck construction upgraded to the full card pool
- Generated-card recognition in the Big Test reporting output

## Still requires precise behavioral parity work

1. **Headlong Charge (Tachiai):** Sacrificing a Kimarite must be optional and controllable; the current automated opening assumes sacrifice whenever one is available.
2. **Kimarite searches and player choices:** Get Underneath currently selects the first eligible opposing Kimarite; Use the Tawara similarly uses a deterministic search. Human and AI decisions need explicit selection where the rules grant a choice.
3. **Read the Move and Pull:** Both modes exist, but the automatic/controller choice policy should be reviewed and tested for the intended human interface.
4. **Tottari:** The exact trigger window for an opponent's prevented/reduced Grip attempt needs a dedicated audit and tests.
5. **Sidestep, prevention, Temporary interaction:** Verify complete interactions with the current approved text before using this as the new official balance baseline.

## Balance/testing gate

- Keep all V5 edits in `feature/v5-integration-controller` / draft PR #16.
- Preserve `local/v45-card-sync` unchanged.
- Do not infer balance from seed-matched comparisons until card effects and pool composition are confirmed.
- Show complete balance and matchup results to the designer; **no card/stat/rule balancing changes without explicit approval**.

## Follow-up parity implementation (October 9, 2026)

The following changes are committed on the V5 branch (no balance changes):

- Headlong Charge Tachiai now accepts an explicit optional per-side sacrifice index; absent/None means decline. The entry point is wired at engine level; interactive pre-bout prompting and AI selection remain to be integrated.
- Exchange Get Underneath and Use the Tawara now accept `kimarite_index` when multiple Kimarite are eligible. The normal human Exchange action supports choices; default engine/AI search behavior remains deterministic, and Tachiai Get Underneath still invokes the default selection path.
- Tottari's opponent Grip-event flag is preserved through the next start-of-turn Kimarite check and cleared afterward, preventing stale eligibility at the end of that turn.
- Added dedicated regression tests for Headlong Charge choices, Kimarite searches, Tottari timing, Sidestep push suppression/resolution, and Read the Move/Pull modes.

**Remaining before baseline certification:** run the full suite (not yet run on these commits), resolve any failures, add human pre-bout selection and deliberate AI policies, verify Sidestep with negative-effect prevention and interrupted Temporaries, and confirm the printed Tottari window against final rules. No new balance baseline has been run.

### AI choice follow-up

- AI Pull now enumerates printed `filter` versus `reversal` modes rather than obsolete `pay_pull_cost` keys.
- AI Read the Move now considers `draw` as well as each valid Temporary removal target, using explicit `mode` values.
- Get Underneath's Exchange search no longer prompts the acting human to choose from the opponent's hidden Draw Pile. Opponent-owned search choice is still a pending dedicated interactive-controller feature; noninteractive search remains deterministic.
- Added regression tests for both AI mode sets.
- **Verification status:** source edits are committed but are not yet test-certified. GitHub Actions minutes are no longer a project constraint because the repository is public; run CI as needed for regression validation. A passing run for the latest commits is still required before baseline certification.

## CI usage policy (updated October 9, 2026)

- The repository is public, so **do not restrict or defer GitHub Actions runs because of the previous monthly minutes cap**.
- Push parity fixes and run relevant regression workflows freely, including the full test suite when appropriate.
- A green CI run validates code/tests, **not** card balance; the balance-adjustment approval gate and V4.5 preservation still apply.

### Interactive search / CI follow-up

- Green CI run #650 confirmed the earlier repaired suite (before the current follow-up commits).
- Human Headlong Charge selection is forwarded through both standard and style bout entry points, and prompted in the terminal.
- When AI Get Underneath targets a human opponent's deck, the search is deferred to that human; the terminal shows only the human's own eligible Kimarite and lets them choose by Draw Pile index. Simulated/noninteractive games still resolve automatically.
- AI Use the Tawara now nominates a card through the engine's explicit search choice, rather than passing the obsolete `lose_position_for_power` key. Normal noninteractive searches retain a deterministic fallback.
- Regression coverage added for opponent-owned human searches and AI Tawara selections.
- **Validation:** current commits are awaiting the next CI result. No official balance baseline should run until CI is green and the pending interaction audit is reviewed.

## Search keyword ruling — October 9, 2026

**Approved rule:** Search is automatic. Starting at the top of the Draw Pile, take the first card matching the category named by Search (for example, Kimarite). Do not look at the deck, reveal multiple candidates, choose among matches, shuffle, or reorder other cards. If no matching card exists, nothing is moved. The found card moves to the destination specified by the calling card's effect.

This supersedes previous proposals for human/AI `kimarite_index` choices and opponent-owned interactive searches. Get Underneath and Use the Tawara resolve by the same automatic topmost-Kimarite mechanism. Deferred-choice state, prompts, and AI ranking policies for Search have been removed. Regression tests enforce top-to-bottom category matching.

## Approved V5 orb override — October 9, 2026

At designer request, **Shiko Stomp** is **1 Power / 1 Technique / 1 Spirit** (previously 0/0/0). This is a deliberate approved balance modification in `src/kimarite/catalog.py`, not a transcription error. The frozen `data/v5_print_pool_snapshot.json` remains unchanged as a historical source snapshot; production V5 catalog takes precedence for this explicitly approved override. Shiko Stomp's persistent Temporary and Tachiai protection effects are unchanged. Any CI round robin after commit `eaf6d2c8` must be treated as a new balance version.
