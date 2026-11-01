# Kimarite build governance — B11 canonical mainline

## Which code is current?

The **`main` branch** is the one authoritative approved build. The latest consolidated B11 release includes the browser interface and player-controlled Tachiai, the 69-wrestler data, current AI and all approved card rules. Do not choose an older branch because its historical label appears more stable or because a simulation was previously run there.

Old `experiment/*`, `feature/*` and `release/b11-playtest` branches can remain as reproducible history, but must not be used as the default starting point for ongoing game development.

## What does "locked in" mean?

When the designer approves a build, rule, card or AI update as the new current version, treat that update as the baseline for all subsequent work. A proposal or test variant remains opt-in only until it is explicitly approved. Do not silently roll back approved changes or substitute an older AI, ring rule, roster, card catalogue or Tachiai flow.

A pull request number alone is not a version number. Before merging, compare its **ancestry** with `main` and the latest B11 user-facing branch, checking that approved functionality is not lost.

## Safe update procedure

1. Read `main` HEAD and review the current approved game state.
2. Start the work branch from that exact mainline commit, not a historical experiment.
3. Apply only the approved changes. Keep old test fixtures compatible without silently changing game mechanics.
4. Run full Python tests, focused B11 browser/Tachiai and Shitate checks, and relevant 69-wrestler validation smoke. Fix failures rather than concealing them.
5. Merge into `main` only when the user-approved feature works and the relevant build checks are green.
6. Record the new commit and ensure future work starts from the updated `main`.

Do not force-push `main` or erase branch histories to make a build appear current. Preserve old experiments as history, not as active builds.

## Current specialist card terminology

- **Recover Push** gains Push only at negative relative Position and stops at zero; **Recover Momentum** likewise only restores negative Momentum toward zero.
- **Shitatedashinage** gates Recover 1 Push, Recover 1 Momentum, **and draw 1** behind Deep Right Grip. An unconditional draw is only a possible future buff.
- **Shitatehineri** with Deep Right Grip plays a chosen legal discarded card for free, then Exhausts that card. Delayed Temporaries remain active until their effects resolve or they are disrupted, then Exhaust.
