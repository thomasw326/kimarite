# Optional difficulty-based stat boosting (NOT ENABLED)

Status: **future design option / OFF by default**. Recorded 2026-10-10.

The design discussed a **seven-step difficulty cycle** for wrestler base stats. A difference of **7 difficulty levels** should correspond to **one full additional stat point**. The intermediate steps should cycle through a progression rather than adding a full stat every level.

This is **separate from the currently active affinity-based deck pruning**:
- There are exactly **15 wrestler archetypes**, not A/B variants.
- Current difficulty controls removal of low-affinity cards from the same archetype's deck.
- **No base stat increase is currently applied** by `build_style()` or the 15-style round-robin tester.
- Enabling a future stat progression must require an explicit opt-in setting, default `false` (for example `enable_stat_boosts=False` or `--stat-boosts`). Never infer it from difficulty alone.

## Unresolved before implementation

The exact order of the seven intermediate stat-cycle steps, which stat receives points for each archetype, and the interaction with stat caps are **not yet specified in this note**. Retrieve prior detailed design decisions if available; do not invent a progression or silently change the six-orb stat builds.

## Acceptance criteria when enabled

1. With the toggle OFF, base stats match today's builds at every difficulty.
2. With the toggle ON, progression is deterministic and uses the agreed seven-step cycle; difficulty values seven apart differ by precisely one full stat-point progression.
3. Applies to the same 15 archetypes without creating additional wrestlers.
4. Tests separately report stat-boost setting and deck-pruning difficulty to prevent confusion.
