# B12 Tsukidashi third-play Push — balance adjustment

Experiment branch: `experiment/b12-tsukidashi-third-play-push-v1`. Based on the fully tested `experiment/b12-oshidashi-pos3-ring4-v1` experiment, commit `0b95aefe67d5774d77cd52775bc6c8e4cc467375`.

## Approved change
Tsukidashi Exchange effect:
**If Tsukidashi is the third or later card played this turn, gain 1 Push.**

This counts Tsukidashi itself as one of the cards played. Remove the previous Exchange effect granting 1 additional Play and drawing 1 card when relative Position was ≥+1. The new Exchange effect does not require positive Position, and does not draw or grant Plays.

Tsukidashi's **Kimarite win requirement** remains unchanged: relative Position ≥+3 and ≥3 cards played this turn. Its orbs remain 🟣🟠🟠.

No other Kimarite rules, stats, deck contents, or AI rules have changed. Retain the prior Oshidashi Position ≥+3 correction and Tachiai ±4 boundary fix.

## Verification
Check card plays numbered 1, 2, 3, 4, position-neutral/negative eligible plays, no replacement draw/Play, and the separate unchanged Kimarite win predicate. The workflow runs the original 60 frameworks × 28/40 modes, same seed `20261102` and mirrored 7,080-bout schedule. Deck blob SHA expected: `92618ce1d60ec8591381f045547dbac3f8b056f3`.

This balance adjustment is isolated from `main`. Compare to the previous 7,080-bout Oshidashi/ring fix run `41551738381` before considering further changes.
