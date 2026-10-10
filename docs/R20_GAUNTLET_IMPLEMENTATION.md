# R20 generic Kimarite gauntlet — implementation notes

**Status (2026-10-10): Schedule and catalogue implemented; combat adapter pending. No R20 bouts have been executed.** This experimental branch is based on the active V5 integration draft. No existing wrestler decks, styles, live card IDs, or balance values are modified.

## Goal

Measure 70 approved variants across 22 Kimarite, separately in **Starting Kimarite** and **shuffled-deck** placement. Do not assign experimental variants to particular named wrestlers or style affinity rankings. Gather raw counts and descriptive results for designer selection; do not auto-pick the "best" card.

The immutable R20 design snapshot is in data/r20_kimarite_arms.json, copied from the [R20 Kimarite A-B Matrix](https://docs.google.com/spreadsheets/d/1JY-vPmU-yqcwYzrEugKP43JrnFGLi_UwZSFkOSqWtWI/edit?gid=1168699165) at rows 6–75. It includes the approved Katasukashi controls and variants, as well as Tsukiotoshi's updated 🟣🟢🟠 and Exchange +1 Play.

## Experimental fixtures

- **18** stat distributions, matching the 108-configuration Big Test roster.
- **6** priority permutations per distribution; **108** generic profiles total.
- **6** distinct, cyclically rotated opposing profiles for each tested profile, without requiring style-based card assignment.
- For every fixture and every arm, test **starting** and **shuffled** placement with **A and B seat orientation**.
- Each pair of seat orientations uses the same fixture seed and the same two generic builds. Compare variants with the *same* fixture IDs and RNG seeds.
- **1,296 bouts per variant per placement**; **181,440 planned bouts** for all 70 variants and two placements.

The schedule is intentionally balanced rather than a complete 108×108 round robin.

### Seat position / game symmetry

This game is largely symmetrical: a fighter taking seat A rather than seat B is not expected to materially affect balance except possible opening Tachiai tie handling, first-mover determination, or implementation defects. **Seat reversal is a diagnostic control, not the primary measure of Kimarite quality.** Record both seats and report unexpected disparities, without allowing seat position to substitute for card win/finish rates.

Seat-mirror fixtures should keep a **fixed role-based deck and RNG stream for each fighter**, not seed decks by seat index. The existing V5 style probe used seat-dependent seeding and did not guarantee same decks after flipping seats; **do not repeat that confound in this gauntlet**.

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

Generates the planned mirrored fixture rows with arm, placement, profiles and seed, without touching the simulation engine.

    pytest -q tests/test_r20_gauntlet.py

Checks the schedule and metric contract locally. Avoid GitHub Actions: the branch was committed with [skip ci].

## Remaining implementation gates before any win rate is valid

1. **Variant-aware Kimarite engine:** all 70 arms must have explicit, tested predicate and Exchange-effect behavior independent of the live card-name dispatch. Existing src/kimarite/kimarite.py and src/kimarite/kimarite_effects.py cannot currently distinguish e.g. OKD-1 from OKD-2.
2. **New Kimarite names / orbs:** implement and test currently absent R20 finishers and planned Utchari rename in the isolated test context, without changing V5 live assignments.
3. **Reversal-event timing:** the five approved Reversal cards (Henka, Pull Temporary branch, Sidestep, Immovable, Kannuki) must record success when their delayed Temporary effect naturally completes/discards, before that wrestler's start-of-turn Kimarite check. Interruption must not count, and a positive outcome is not required.
4. **Generic bout construction:** add a combat adapter from fixtures to fighter state, including variant slots and copy-exclusion parity in both Starting/Shuffled modes. Keep fighter-specific RNG independent of A/B seat.
5. **AI compatibility:** ensure AI knows how to use the variant's Exchange actions, card access, required setup, and finish checks. Fail loudly for any missing implementation; do not substitute a legacy same-name effect.
6. **Dry-run checks:** use local unit tests and a small group of completed bouts with explicit variant attribution and no turn-limit/errors; only then start bounded local batches. Keep production V5 and existing 15 Sumo Styles unchanged.
7. **Logs:** emit a setup/version manifest (source design SHA, git commit, seed policy, active effects), raw per-bout records, summaries per variant/placement, and separate seat-diagnostic reports.

**No simulation data exists for R20 yet.** The 181,440 figure is the planned experimental sample, not reported results.
