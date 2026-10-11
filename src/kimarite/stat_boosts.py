"""Optional seven-step difficulty stat boost. Disabled by default at callers."""
from __future__ import annotations

BOOSTS = (
    (),
    ("tertiary",),
    ("secondary",),
    ("primary",),
    ("secondary", "tertiary"),
    ("primary", "tertiary"),
    ("primary", "secondary"),
)

def boosted_stats(stats, priorities, difficulty: int, *, enabled: bool = False):
    """Return (Power, Technique, Spirit) after optional seven-step boosts.

    Priority entries are Stat enums ordered primary, secondary, tertiary.
    Duplicate priorities (e.g. Power/Power) require a deterministic unique
    ordering; treat missing stats as secondary then tertiary, placing the
    numerically lower remaining stat in the tertiary slot.
    """
    if not enabled:
        return tuple(stats)
    if difficulty < 0:
        raise ValueError("difficulty must be nonnegative")
    from .models import Stat
    indices = {Stat.POWER: 0, Stat.TECHNIQUE: 1, Stat.SPIRIT: 2}
    chosen = []
    for stat in priorities:
        if stat not in chosen:
            chosen.append(stat)
    remaining = [stat for stat in indices if stat not in chosen]
    remaining.sort(key=lambda stat: (-stats[indices[stat]], indices[stat]))
    chosen.extend(remaining)
    # For a repeated primary/secondary, the lower remaining stat is tertiary.
    chosen = chosen[:3]
    cycles, remainder = divmod(difficulty, 7)
    output = [value + cycles for value in stats]
    roles = dict(zip(("primary", "secondary", "tertiary"), chosen))
    for role in BOOSTS[remainder]:
        output[indices[roles[role]]] += 1
    return tuple(output)
