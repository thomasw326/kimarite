# Optional difficulty stat boosts — seven-step cycle

Status: **implemented as an opt-in design rule; OFF by default.**

Every **7 difficulty levels** produce a full **+1 to all three base stats** relative to the previous seven-level block. Intermediate steps distribute boosts according to the wrestler's **primary / secondary / tertiary stat priorities**, not dynamically re-sort the numerical stats after boosting.

| Difficulty remainder (mod 7) | Boosts within the cycle |
|---|---|
| 0 | None |
| 1 | Tertiary (lowest priority) |
| 2 | Secondary |
| 3 | Primary (highest priority) |
| 4 | Secondary + Tertiary (both other than primary) |
| 5 | Primary + Tertiary |
| 6 | Primary + Secondary |
| 7 (next cycle's 0) | All three, +1 each |

Implementation formula for nonnegative integer difficulty `d`:

- `full_cycles, remainder = divmod(d, 7)`
- Begin with `base_power/base_technique/base_spirit + full_cycles` each.
- Apply the extra boosts for the remainder in the table.

Example: Difficulty 7 = base + (1,1,1); difficulty 8 = base + (1,1,1) plus tertiary; difficulty 14 = base + (2,2,2).

**Important interpretation:** "lowest / secondary / highest" here is anchored to the wrestler's assigned *tertiary / secondary / primary* priorities. Do not recalculate relative numeric lows and highs each step; otherwise the intended seven-step pattern can change unexpectedly.

## Default-off policy

- Exactly **15 wrestler archetypes**; difficulty doesn't create A/B wrestlers.
- `enable_stat_boosts=False` by default. Stat boosting must never turn on merely because difficulty increases.
- Affinity-based deck pruning is separate, and may be enabled for difficulty even when stat boosts are OFF.
- Current base builds and stat caps should not be silently changed. If cap rules conflict with optional boosts, discuss before adopting boosted results into canonical balance testing.
