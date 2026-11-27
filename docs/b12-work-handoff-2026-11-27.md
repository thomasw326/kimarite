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
