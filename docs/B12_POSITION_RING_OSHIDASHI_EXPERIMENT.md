# B12 Oshidashi +3 Position and full Tachiai ring — approved experiment

Based on the corrected pooled-Push B12 experiment at commit `be92a95e96eeeebf72a5c844803342fa2055bb16`.

## Changes
- Tachiai Push uses the shared rules' `POSITION_MIN=-4` / `POSITION_MAX=+4`: four net Push from neutral ends at ±4; only fifth net Push crosses the ring boundary.
- Oshidashi Kimarite win condition now requires relative Position **≥ +3** (was ≥ +2), with its existing Momentum **≥ +2** requirement unchanged.
- **No other Kimarite, card stats/orbs, decks, AI behaviours, Spirit Push thresholds or Power blocking thresholds change.** Okuridashi, the separate generated-only Kimarite, remains at ≥ +2 Position unless separately approved.
- The existing 60-framework design snapshot is verified by the original blob SHA `92618ce1d60ec8591381f045547dbac3f8b056f3`. Same 28/40 cards, 15×4 AI grouping and seed 20261102.

## Baseline observations
The preceding corrected 7,080-bout B12 test recorded 1,060 Oshidashi finishes, 59.4% bout win rate when Oshidashi was played (969/1,631), and 53.4% win rate across all decks starting with Oshidashi (2,143/4,012). These are descriptive, not a causal impact estimate.

Other positive-Position Kimarite played win rates: Tsukidashi 62.0% (954/1,539); Oshitaoshi 54.4% (760/1,397); Yorikiri 47.9% (443/925); Yoritaoshi 47.3% (494/1,045); Kimedashi 45.6% (31/68). The generated-only Okuridashi has no ordinary played sample.

The preceding 7,080 bout records have zero direct Tachiai ring-outs; fixing the separate boundary issue may have no effect on these seeded openings. A new seeded run is needed to measure the specific impact of the Oshidashi threshold change.

Scope intentionally restricted to this experimental branch; no changes to `main`.
