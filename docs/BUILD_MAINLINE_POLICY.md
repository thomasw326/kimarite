# Kimarite build governance — latest approved and tested build

## Which code is current?

**The current game is the latest designer-approved, successfully tested playable build — not whichever historical commit happens to be named `main`.** Keep `main` updated to that build so the branch remains a useful canonical entry point. If an experimental branch has become the approved and best tested build, **promote its complete working tree to `main`**, not the other way around.

On 16 November 2026, the tested B12 second-pass gameplay snapshot from `experiment/b12-shikiri-exchange-plus-play-v1` was promoted intact to `main` in commit `8678e487`. The preceding main snapshot is preserved as `archive/main-before-b12-second-pass-promotion-2026-11-16`. The source B12 batch completed 35,400 bouts successfully on commit `884fef39`; documentation-only changes followed.

## Wrestler roster policy

The current B12 wrestler design target is **60 frameworks**. The older 69-wrestler design sheets and references are historical, not a planned nine-wrestler expansion. The browser currently implements a 26-wrestler B9-derived roster; integrating and validating the 60-wrestler target is a release task. Do not misstate the 26 as the target or the 69 as the current plan.

## What counts as an approved build?

- Explicit designer approvals supersede older build labels, card snapshots, AI variants and release locks.
- A proposed or untested new feature is not automatically part of the release build. Record its approval separately and implement/test it before including it in a promoted gameplay snapshot.
- Do not silently revert previously approved rules, orb colors/counts, Tachiai flow, AI, wrestler decks or Kimarite conditions.
- The full game's playable behavior is determined by its versioned source tree, not by a stale spreadsheet introduction, historical README paragraph or older release tag.
- Preserve former baselines for reproducibility without treating them as the release target.

## Promote a newer tested snapshot

1. Identify the complete latest designer-approved, successfully tested candidate **including the actual Human vs AI implementation**. Record its full commit SHA, test evidence and any post-test documentation-only commits.
2. Preserve the prior `main` SHA in an archive branch.
3. **Promote the candidate's exact source tree**. Do not cherry-pick, back-port or individually reconcile approved card changes against an outdated `main` as though the old tree were authoritative.
4. Prefer a non-destructive merge commit that keeps both histories while choosing the new candidate tree. Avoid force-pushing or erasing previous work.
5. Run full Python tests, B11 browser/Tachiai and Shitate tests, wrestler validation and relevant smokes on the resulting new `main` commit. Investigate failures; don't call an unverified promotion a release candidate.
6. Record the new SHA, evidence and known gaps in the Kimarite itch.io release roadmap's BUILD AUDIT and Release Checklist.
7. Start subsequent gameplay development from the promoted `main` unless a newer approved and tested branch is designated.

The release roadmap Google Sheet is the cross-chat project index:
https://docs.google.com/spreadsheets/d/1YCAG7skE06kPsjadfWr_L7CYDCK_G2HJ68GcvadZcLk/edit

## Current specialist card terminology

- **Recover Push** gains Push only at negative relative Position and stops at zero; **Recover Momentum** likewise only restores negative Momentum toward zero.
- **Shitatedashinage** gates Recover 1 Push, Recover 1 Momentum, **and draw 1** behind Deep Right Grip. An unconditional draw is only a possible future buff.
- **Shitatehineri** with Deep Right Grip plays a chosen legal discarded card for free, then Exhausts that card. Delayed Temporaries remain active until their effects resolve or they are disrupted, then Exhaust.
