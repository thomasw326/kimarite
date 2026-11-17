# B12 card rebalance — 35,400-bout paired-seed comparison

Based on the successful original 35,400-bout card-strength test, with identical 60 decks, 15 style AIs, two deck modes, 5 repetitions and the same seed (20261102).

Approved changes being tested:
- Shiko Stomp: unconditional +1 Momentum; independently check **pre-play Position lead** for +1 Power, and **pre-play Power lead** for +1 Push. No chaining.
- Deashi: reduce Spirit from 2 to 1 orb (Power 2, Technique 0, Spirit 1); same Exchange effect.
- Belt Slap remains unchanged at Power 2 / Technique 0 / Spirit 3.
- Butsukari: if leading Power, opponent loses **2** Power (was 1), subject to prevention. Momentum-to-Unstable and own mill 1 unchanged.
- Get Underneath unchanged; tests confirm its existing opponent-draw-pile Kimarite search and no-search cases.

Experimental branch only; **no changes to the 60 source wrestler decks**, and no main-branch merge.
Both modes: 1770 unordered pairings × two seats × five repeats = 17,700 bouts each, 35,400 total.
Report outputs: played-vs-unplayed, prepared Tachiai, designated top deck, inclusion/copy counts, starting/deck-origin and finishing Kimarite, win methods, contributions, exposure and timing.
No causal interpretation of played-vs-unplayed; compare win rate shifts and card-role deltas within deck and by mode, noting sampling uncertainty.

## Second-pass card-review approval set — 6 November 2026

The following changes are implemented on the B12 review branch and are the
**only additional card-balance changes approved** for the next comparison.
The historical text above describes the *first* rebalance run, not current rules.

- Get Underneath: when played during Exchange while Exhausted (7+ discarded),
  its owner becomes Unstable. Tachiai has no new penalty.
- Nekodamashi: remove the -1 Momentum penalty if its Temporary is disrupted.
- Denshamichi and Spin Away: swap disrupted generated Okuri finishers.
  Denshamichi grants opponent **Okuridashi** and reverses Position;
  Spin Away grants opponent **Okuritaoshi** without the Denshamichi Position flip.
- Explosive Step — Fumikomi: Exchange grants +1 Push at any Momentum; mills 2.
  Tachiai Spirit conditional, orbs 🟠🟠 and milling unchanged.
- Chiri-chozu: reduce orbs to 🟣🟢🟠 (1 Power, 1 Technique, 1 Spirit).
  Permanent Temporary trigger unchanged.
- Salt Throw: Exchange moves the entire Discard Pile to the bottom of the Draw
  Pile without a size threshold; other effects and five orbs unchanged.
- Shikiri: Exchange grants +1 Play and enters its permanent Temporary;
  Tachiai only enters the Temporary; keep orbs 🟣🟢🟢🟠🟠.
- Sheer Grit: **retain unchanged**; strong performance in its current decks is
  insufficient justification for an immediate nerf.

### Rerun protocol

- Keep the original 60 deck JSON checksum and both 28 / 40 modes; existing
  style AI and its 15-by-4 mapping remain unchanged.
- Same seed **20261102**, 1,770 unordered matchups, mirrored directions,
  five repeats per deck mode; target **35,400** completed bouts.
- Smoke/test gate before 24 shards; aggregation must reject missing or
  duplicate bouts, errors, and nonmirrored pairs.
- In addition to per-framework outputs, `card_role_comparisons.csv` explicitly
  reports win rates and sample sizes for **included vs excluded**, **Tachiai
  selected vs not selected among included decks**, **top-deck selected vs not
  selected among included decks**, and **Exchange played vs not played among
  included decks**, both by deck mode and combined.
- Observational split results should not be presented as causal effects.
- Review outcomes before any further changes to the 60 wrestler decks or main.

## Results review — 7 November 2026

The second-pass 35,400-bout comparison [completed successfully](https://github.com/thomasw326/kimarite/actions/runs/42322655349). For per-card role splits, first-pass deltas, win-condition changes, sample-size caveats and follow-up priorities, see [B12_SECOND_PASS_35400_RESULTS_REVIEW.md](B12_SECOND_PASS_35400_RESULTS_REVIEW.md). Results were reviewed without any further card changes, deck edits or release-lock changes.
