# B12 Work handoff — 27 November 2026

## Source of truth
- Main: a4286b3678a4b7fa4748800fdb6bdbac9e978d68; four anti-Grip cards already integrated.
- Active experiment: `experiment/b12-next-card-review`; implementation/test reconciliation efb1328.
- Current review spreadsheet: https://docs.google.com/spreadsheets/d/11-qC5jKJK9nFDl27d4ITYGY2ugygd92O-3zsJxVcf7k/edit#gid=1201201299
- Archived 35,400-bout baseline: same spreadsheet gid 2125465057.
- Latest completed balance test: https://github.com/thomasw326/kimarite/actions/runs/46023449322 (commit 8a9003f, artifact 15211795813). 17,700 max40 bouts, 60 frameworks, 1,770 pairs, five mirrored repetitions, seed 20261102, zero simulation failures. Previous comparison run 46017071410 artifact 15205694757. The new seat-selection changes are NOT represented in this completed batch.
- Live preview: https://kimarite-b12-alpha-preview.onrender.com ; deployment parity not verified.

## Approved decisions
- Hazuoshi: 1/1/1 orbs; +1 Push, reduce opposing Grip one level, Unstable if actually reduced.
- Maesabaki: 0/2/2; remove all opposing Grip in one hand and disrupt one opposing Temporary; draw once if either fails.
- Kannuki: 2/1/0; suppress opponent Grip benefits, not Grip gain; next own turn remove all opposing Grip and +1 Momentum if Temporary survives.
- Ottsuke: 1/1/1; reduce opposing Grip one level, +1 Momentum, Temporary blocks establishing/improving opposing Grip until next own turn.
- Salt Throw: 1/1/3; Tachiai printed orbs only. Exchange: If Exhausted (7+ discard cards), gain 1 Momentum and 1 Push. Return all discard cards to bottom of deck. No extra Play or Temporary. Implementation checks condition before recycling; note current implementation recycles before applying bonus, despite wording ordering.
- Ankogata: retain printed orbs; +1 Power; permanent Temporary blocks opponent card effects reducing Power or making owner Unstable. No protection from exhaustion, own effects, empty deck, or existing Unstable.
- Renzoku: retire from new offers and AI frameworks; historical definition and ID preserved. Existing owned cards grandfathered; prior draft offer replay supported. Eleven slots in frameworks 06,10,15,23,25,36 replaced by Mawashi Reversal (1/2/0). No other framework changes.
- Mawashi Reversal: unchanged; if usable Grip leads, flip negative Position to positive same distance, otherwise +1 Push/+1 Momentum when nonnegative. Flag deck fit; not a buff candidate solely based on current placement.
- Automatic Grip selection: shallower own/deeper opposing hand first; acting seat A left, B right on ties. Explicit hand choices unchanged; AI finisher tie exception removed. Commit fddca3b.
- After card audit: review all 60 AI decks for synergy, AI compatibility, duplicated cards, and Grip/hand fit. Do not rebalance every deck mid-audit.

## Verification / remaining work
- Previous full CI 46027469755: 1067 passed, 9 failed (7 obsolete Salt Throw tests, 1 obsolete AI tie test, 1 seeded draft test). Canonical smoke 46027469737 failed same draft assertion.
- efb1328 reconciles tests, validates pre-retirement offer histories, retains inherited retired cards in owned-card pool, and removes Renzoku from active offer/tuning pool. CI 46029099370 and canonical smoke 46029099294 pending at handoff; check actual conclusions before merging.
- Verify regression results and any additional failures. Do not merge red CI. Restore release workflow isolation: experimental large-batch workflow and report mode changes should not accidentally replace unrelated release settings.
- Verify all current sheet rates against downloaded CSVs, with max40 only; compare exact counts, not rounded display values. Latest artifact is available via run. All delta formulas: inclusion E-F, played G-H, Tachiai L-M, top deck N-O, percentage points. Total sum only when four metrics exist; blank for incomplete rows. Cohorts for last three conditioned on deck inclusion. Association not causal.
- Sync consolidated catalogue and 60 proposed 28+12 deck sheet, preserving historical records; flag experimental vs main. Check Render deployment after eventual merge.
- Before next batch ensure Salt Throw execution order matches agreed wording; terminal-win behavior requires explicit regression coverage. Current batch reflects old order.
- No need for another dedicated large batch solely for these changes before continuing card audit. Next batch should include seat rule and all subsequently approved changes, then update active audit and preserve previous snapshot.

## Continuation checkpoint — later 27 Nov 2026
- Earlier full pytest 46029099370 and canonical smoke 46029099294 both success at efb1328.
- Salt Throw approved bonus-before-recycle order implemented in 09aa151; terminal ringout no-followup regression test added in 0d3d173. Later commits are not covered by the earlier green CI.
- Diagnostic artifact 15211795813 reconciled against active B12 Card Audit CSV: 928 rate/count, 347 delta and 174 finish entries verified; 1,449 checks, zero discrepancies.
- Exact active sheet snapshot preserved in docs/b12-audit-sheet-snapshot-2026-11-27.json; archived 35,400-bout baseline untouched.
- All 60 current experimental decks match the 60 Proposed 28+12 sheet exactly; each has 28 unique base cards and 12 duplicated base cards; no Renzoku slots. docs/b12-60-framework-audit-2026-11-27.md documents per-framework suitability flags and shared-style AI limitations.
- Historic 60-Framework Reconciliation tab still includes older Renzoku suggestions; retain as superseded history, not the current authoritative deck source.
- No deck or approved mechanics alterations made beyond Salt Throw sequencing to match previously approved wording.
- Release gate: confirm post-change CI; ensure experimental workflow does not contaminate release settings; verify deployment parity before any merge. Next balance test must include seat selection and Salt Throw ordering and preserve old snapshot.

## Workflow isolation confirmation
- Restored .github/workflows/b12-60-framework-big-test.yml to the *exact* main-branch blob f125efd335806a5afaacac742b3296504e046dbf.
- Moved experimental 17,700-max40 workflow to .github/workflows/b12-experimental-next-card-review.yml (commit 934f259) with its own branch/path trigger.
- Main-to-experiment diff now contains only the **new** isolated experimental workflow, not a modification of the historical B12 comparison workflow.
- Existing efb1328 full CI/smoke success does **not** cover later Salt Throw order or the new test. No merged release or verified Render deployment as of this checkpoint.

## Explicit owner approval — Momentum cap and 70,800-bout run
- Owner confirmed all reviewed Position boundaries, ringout, Push prevention and resistance mechanics as intended except Momentum overflow. Excess Momentum is lost at ±3; it never becomes Push or causes a ringout. No other card or deck mechanics changed in this correction.
- Engine e29f239 and regression tests 4736b55; tests cover both seats, edge, Momentum loss, defensive Temporaries and Side-by-Side. Full CI required before large batch.
- Next max40 run: 60 unchanged frameworks, 1,770 pairings, 20 mirrored repetitions, 70,800 bouts, seed 20261102. Preserve previous artifact 15211795813 and sheet snapshots. New run also includes previously approved Salt Throw order and Grip seat-selection changes, so comparison against 17,700 results is not a pure overflow-only experiment. Compare first five repetitions separately if exact paired attribution is needed, and acknowledge other changes.
- Do not replace historical results or update current card/wrestler success tables until complete artifact coverage and zero simulation failures verified. Analyze inclusion, actual Exchange plays, prepared Tachiai, top-deck, Kimarite finishing origin, ringout share, framework/matchup changes and card contributions; no further nerfs without owner approval.

## Owner-approved Tsukitaoshi review
- Tsukitaoshi now requires relative Position >= 0 and at least four cards played this turn. Orbs and Exchange unchanged. Engine f8f158a; inspector 70c14ed; victory checklist dc11649; AI progress predicate 2581072; mirrored regression 96fb26c.
- Retain Tsuppari, Tsukidashi and Oshidashi unchanged at this stage. Owner notes ringout-heavy winning frameworks can inflate inclusion success while competing with Kimarite finish opportunities. Analyze conditional finishing opportunities, not just raw deck win rates.
- Preserve 70,800-bout no-overflow results (run 46037904715, artifact 15220130235) as pre-Tsukitaoshi-change evidence. No new large batch solely for this change; CI pending.

## Owner-approved Tsuppari review
- Supersedes earlier retain decision: Exchange mill 2 instead of 1, with all other effects/orbs unchanged. Engine 4dce79a, inspector 993c70c, regression 254f431, terminal descriptions (also Tsukitaoshi) 0e6b951. CI pending; preserve existing 70,800-bout evidence as pre-nerf. Continue Fumikomi review before further simulation.

## Owner-approved Fumikomi review
- Exchange: gain 1 Momentum, then gain 1 Push only if not Exhausted (discard count below existing 7-card threshold). Remove milling; interpreted as both Tachiai and Exchange. Retain Tachiai Spirit-win +1 Push and 0/0/2 orbs. Existing conditional Exchange implementation verified; mill removal 519b305 / 0589f7e, inspector and terminal 170d3e1 / a27bdb7, regression tests 70923c5 / 16710a8 / b5c6b4f. CI pending. Preserve 70,800-bout pre-nerf results; no new large batch yet.

## Owner-approved Denshamichi review
- Option A: remove delayed +1 Momentum; retain immediate +1 Push, Temporary next own turn +1 Push, and disruption granting opponent Okuridashi and reorienting Position toward opponent. Orbs 1/0/2 unchanged, Tachiai printed only. Engine 0426a5c, inspector f3c614c; updated mirrored survival regression and retained disruption tests. CI pending; preserve 70,800-bout pre-change evidence. No new batch yet.

## Owner-approved Nokotta! review
- Exchange: if relative Position is negative, gain 2 Push; otherwise draw 1 card (no Push). Retain printed orbs 1/0/2 and Tachiai printed only. Engine fc25539, inspector 13cb672; mirrored regression added for negative, neutral, positive and edge positions. CI pending; retain pre-change 70,800-bout results. No other changes.

## Owner-approved Belt Slap review
- Option E: Exchange gain 1 Momentum, then gain 1 Push only if recorded Tachiai Spirit advantage >= 3. Keep orbs 2/0/3 and Tachiai printed only. Engine 55e05c1, inspector ffc2932, terminal d9a92af; mirrored threshold regression updated. CI pending. Preserve 70,800-bout pre-review results, no new batch yet.

## Owner-approved Shiko Stomp review
- Option B: remove unconditional +1 Momentum. Preserve independent pre-play Position lead -> +1 Power and Power lead -> +1 Push, 1/0/4 orbs and printed-only Tachiai. Engine f5443f5, inspector 67e83ff, updated tests 65e90ab, terminal description 7a825c9 (corrects old Sonkyo text). No Sonkyo or other mechanics changes. CI pending; preserve pre-review 70,800-bout evidence.

## Approved seven-card batch — 35,400 bouts
- Owner requested regular 35K batch after failed validation. Both 46054265088 and 46054284663 failed only tests/test_v42_approved.py::test_approved_kinematic_finishes (1114 passed); obsolete expectation allowed Tsukitaoshi at -2 Position. Corrected assertion and added neutral-position/negative-Momentum success in 86c57a3; no mechanics changed.
- Workflow 558e37d uses 60 unchanged frameworks, 1,770 pairs, 10 mirrored repetitions, seed 20261102, 24 shards, max40 only, exactly 35,400 bouts, 1,180 per framework. Full pytest and smoke gates remain. Automatic push trigger now limited to experimental workflow file, avoiding accidental large batches during incremental reviews; manual dispatch retained. Preserve historical workflow and 70,800 baseline, update audit after verified completion.

## Owner lock decision after 35,400-bout validation
- LOCKED / good to go: Tsukitaoshi, Fumikomi, Denshamichi, Nokotta!, Belt Slap, Shiko Stomp; previously approved grip-removal cards Hazuoshi, Maesabaki, Kannuki, Ottsuke also locked.
- OPEN: Tsuppari retains implemented mill 2 pending further review; no rollback or additional mechanics change.
- Run 46054703948 success, all 24 shards and aggregation passed, artifact 15225644265, tested 558e37d. Master catalogue and current audit decision columns updated; audit numerical evidence remains 70,800 pre-nerf baseline until separate reconciliation. No merge or deployment authorized.
