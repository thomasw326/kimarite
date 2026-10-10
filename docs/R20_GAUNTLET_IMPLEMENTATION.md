# R20 generic Kimarite gauntlet — implementation notes

**Status (2026-10-10): 70-arm catalogue, generic combat adapter, variant win/Exchange dispatch, R20 Reversal timing, tactical AI choices, local batch runner and CSV reporting implemented. Tests are authored but have NOT been executed or verified. No R20 bouts have been run.** This experimental branch is based on the active V5 integration draft. No existing wrestler decks, styles, live card IDs, or balance values are modified.

## Goal

Measure 70 approved variants across 22 Kimarite, separately in **Starting Kimarite** and **shuffled-deck** placement. Do not assign experimental variants to particular named wrestlers or style affinity rankings. Gather raw counts and descriptive results for designer selection; do not auto-pick the "best" card.

The immutable R20 design snapshot is in data/r20_kimarite_arms.json, copied from the [R20 Kimarite A-B Matrix](https://docs.google.com/spreadsheets/d/1JY-vPmU-yqcwYzrEugKP43JrnFGLi_UwZSFkOSqWtWI/edit?gid=1168699165) at rows 6–75. It includes the approved Katasukashi controls and variants, as well as Tsukiotoshi's updated 🟣🟢🟠 and Exchange +1 Play.

## Experimental fixtures

- **18** stat distributions, matching the 108-configuration Big Test roster.
- **6** priority permutations per distribution; **108** generic profiles total.
- **6** distinct, cyclically rotated opposing profiles for each tested profile, without requiring style-based card assignment.
- For every fixture and arm, test **starting** and **shuffled** placement **once each**, not as a double seat-mirrored series.
- Alternate the subject's seat deterministically across opponent samples (3 on A and 3 on B per generic profile). Every arm and both placements use the *same* fixture/seat combinations and RNG seeds.
- **648 bouts per variant per placement**; **90,720 planned bouts** for all 70 variants and two placements (exactly half of the original mirrored plan).

The schedule is intentionally balanced rather than a complete 108×108 round robin.

### Seat position / game symmetry

This game is largely symmetrical: a fighter taking seat A rather than seat B is not expected to materially affect balance except possible opening Tachiai tie handling, first-mover determination, or implementation defects. **We do not schedule reversed-seat rematches.** Instead, we distribute the single assigned seat evenly across fixtures, retaining the seat field only as a lightweight diagnostic and never selecting cards by seat-specific win rates.

Every fixture keeps a **fixed role-based deck and RNG stream for each fighter**, not a deck seeded by seat. This ensures variants and placements are comparable without adding reversed-seat bouts.

## Metrics: report, don't rank

Report separately for each (arm_id, placement):

1. Scheduled, completed, incomplete and error bouts (raw counts).
2. **Bout win rate**: all subject wins / completed subject bouts.
3. **Kimarite completion rate**: wins *specifically by that tested variant* / completed subject bouts.
4. Condition-attainment rate: bouts where the variant's full finish predicate was ever true / completed bouts.
5. Availability rate: bouts where the experimental card was available (hand or Kimarite Zone) / completed bouts.
6. Completion given availability: wins by tested Kimarite / bouts where that card was available.
7. A/B seat counts, with seat-specific wins as an optional diagnostic.
8. Where possible, conditional breakdown by stat build, priorities and opponent build.

No weighted score, no automatic winner, no balance changes. Preserve the raw records to support nuanced human selection.

## Starting versus shuffled

- **Starting:** one specified experimental variant enters the player's Starting Kimarite slot / Zone at setup. Do not also put another copy of it in the shuffled cards.
- **Shuffled:** the experimental variant is not automatically available at setup; place exactly one copy into the normal shuffled card population. The wrestler still receives a normal baseline starting Kimarite, selected independently of their profile and **held fixed across same-family variant comparisons**.
- In both modes, remove unwanted duplicates by card identity and card name; protect all other experimental variant IDs from mixing into the test.
- Preserve supporting-card randomness without specializing decks based on the tested Kimarite. Baseline opponent draws and setup remain fixed between test arms.

## How to inspect the schedule locally

From a checkout of this experimental branch:

    python -m kimarite.r20_gauntlet

Prints JSON planning totals. It **does not run bouts**.

    python -m kimarite.r20_gauntlet --plan-csv artifacts/r20-plan.csv

Generates one scheduled fixture row per arm, placement and generic matchup, preserving its chosen seat and seed without running combat.

    pytest -q tests/test_r20_gauntlet.py

Checks the schedule and metric contract locally. Avoid GitHub Actions: the branch was committed with [skip ci].

## Windows one-command smoke (local only)

In a PowerShell terminal at the experimental branch checkout, run:

    powershell -ExecutionPolicy Bypass -File scripts/r20_local_smoke.ps1

This runs unit checks first and stops on failures. Only if they pass, it runs 160 local sample bouts across Hikiotoshi, Okuridashi, Tsukiotoshi and Katasukashi in both Starting and Shuffled placements. It then produces CSV and JSON descriptive summaries. It does not trigger GitHub Actions, and uses no Actions minutes.

## Smoke-and-go full tournament (Windows local)

Run from a PowerShell session in the experimental branch checkout:

    powershell -ExecutionPolicy Bypass -File scripts/r20_local_full.ps1

This command runs the R20 unit tests and 160 smoke bouts first. It **stops without starting the full tournament** if tests fail, any smoke bout is incomplete, or any smoke error is recorded. If clean, it runs the 90,720-bout single-seat schedule in **216-bout checkpoint chunks**, saving the raw CSVs to artifacts/r20_full. Rerunning the command resumes existing verified checkpoint files; a seed, chunk-size, max-turns or frozen design-catalogue mismatch halts rather than mixing incompatible data. On completion, variant_placement_summary.csv, generic_profile_breakdown.csv, seat_diagnostics.csv, errors_and_incomplete.csv and report.json appear in artifacts/r20_full/report.

The script is local only: it doesn't invoke GitHub Actions or alter V5 wrestler builds. It has not been executed in the current assistant environment because that environment cannot clone or run the connected GitHub checkout.

## Running local batches (no GitHub Actions)

Use a local Python 3.11+ checkout of this experimental branch. No changes are made to live V5 wrestlers or style assignments.

First run the structural and combat tests:

    python -m pytest -q tests/test_r20_gauntlet.py tests/test_r20_variant_runtime.py tests/test_r20_gauntlet_report.py

Then use a bounded smoke batch to validate actual completion and absence of exceptions:

    python -m kimarite.r20_gauntlet_bouts --arm HIK-3 --count 20 --output artifacts/r20_hik3_smoke.csv

For both Starting and Shuffled coverage, use a complete one-arm 1,296-bout batch, then aggregate:

    python -m kimarite.r20_gauntlet_bouts --arm HIK-3 --count 1296 --output artifacts/r20_hik3_full.csv
    python -m kimarite.r20_gauntlet_report artifacts/r20_hik3_full.csv --output-dir artifacts/r20_report

A complete all-arm schedule currently plans 90,720 bouts. Use repeated --start offsets and --count to checkpoint local batches; never launch the full simulation before unit tests and short smoke batches pass. Report inputs are de-duplicated by arm, placement, fixture, seat and seed.

**Important setup policies:** Role-based seeds keep each wrestler's deck stable across arms; seat assignments are even across fixtures without mirror rematches. Both generic wrestlers decline Headlong Charge's optional sacrifice, avoiding accidental removal of the experimental starting Kimarite. All other effects retain the current engine behavior except the expressly gated R20 changes. All five approved Reversals complete naturally before the R20 start-of-turn Kimarite check.

## Remaining implementation gates before any win rate is valid

1. **Validate variant-aware Kimarite engine (code added; tests unrun):** All 70 arms must have explicit, tested predicate and Exchange-effect behavior independent of the live card-name dispatch. Existing src/kimarite/kimarite.py and src/kimarite/kimarite_effects.py cannot currently distinguish e.g. OKD-1 from OKD-2.
2. **Verify experimental names / orbs (catalogue and constructors added):** implement and test currently absent R20 finishers and planned Utchari rename in the isolated test context, without changing V5 live assignments.
3. **Verify Reversal-event timing (R20-only code added):** the five approved Reversal cards (Henka, Pull Temporary branch, Sidestep, Immovable, Kannuki) must record success when their delayed Temporary effect naturally completes/discards, before that wrestler's start-of-turn Kimarite check. Interruption must not count, and a positive outcome is not required.
4. **Validate generic bout construction (code added):** add a combat adapter from fixtures to fighter state, including variant slots and copy-exclusion parity in both Starting/Shuffled modes. Keep fighter-specific RNG independent of A/B seat.
5. **Validate AI compatibility (experimental choice and progress code added):** ensure AI knows how to use the variant's Exchange actions, card access, required setup, and finish checks. Fail loudly for any missing implementation; do not substitute a legacy same-name effect.
6. **Dry-run checks:** use local unit tests and a small group of completed bouts with explicit variant attribution and no turn-limit/errors; only then start bounded local batches. Keep production V5 and existing 15 Sumo Styles unchanged.
7. **Logs:** emit a setup/version manifest (source design SHA, git commit, seed policy, active effects), raw per-bout records, summaries per variant/placement, and separate seat-diagnostic reports.

**No simulation data exists for R20 yet.** The 90,720 figure is the revised planned experimental sample, not reported results.
