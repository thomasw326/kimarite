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
