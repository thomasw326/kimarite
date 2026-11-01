# B12 — Approved engine release lock

**Status:** Locked baseline for subsequent development.  
**Approved snapshot:** `414f09ac696fbbaa6560626c823742f1b822c544` (canonical B11 merge on `main`).  
**Snapshot branch:** `release/b12-locked` — keep this branch pinned to the approved commit; do not develop on it.  
**Current development branch:** `main` — work must branch from this current mainline, never from an older experiment.

## What B12 means

B12 is the name of the **approved and consolidated B11 gameplay engine**. This release milestone does **not** introduce gameplay or balance changes. It records the already merged B11 game as the next baseline, without reinstating superseded mechanics.

The snapshot includes the B11 player-controlled Tachiai, Exchange and card engine, Human vs AI browser gameplay, approved Shitate family and Recover / replay / Exhaust features, and the existing AI architecture. The previous PR #52 integration suite reported 561 passed, with the B11 release smoke reporting 31 passed on its checked commit.

## Deliberately not locked as final

The provisional 69-wrestler design data contains placeholder card selections; it is **not** approved as a final roster or balance baseline. No changes to the 26 existing browser playtest wrestlers or their deck compositions are required for this naming milestone. The version name alone does not establish live deployment parity.

## Release governance

1. Start new wrestler and card work from current `main`, identifying it as **B12 baseline**.
2. Keep `release/b12-locked` unchanged as a readable rollback reference.
3. Only approved gameplay changes may alter the current baseline; confirm them with targeted and full tests before merging.
4. Future build numbers should advance when the user approves a new release lock, not because a PR is numbered higher.
5. Historical `B11`, `B10`, `B9`, and `V5` references in implementation or test identifiers remain historical where necessary; do not silently alter their gameplay assumptions for cosmetic renaming.

**This lock is a branch snapshot, not a Git annotated tag.** It records the commit SHA explicitly to remain verifiable even if a branch reference is changed later.
