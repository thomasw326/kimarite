from __future__ import annotations

from .models import BoutState, Side


def prevent_negative_effect(
    state: BoutState,
    target_side: Side,
    *,
    source: str,
    description: str,
) -> bool:
    """Consume Shiko Stomp to prevent one opposing negative effect.

    Returns True when the effect was prevented.
    """
    fighter = state.fighter(target_side)
    for instance in list(fighter.temporary_zone):
        if instance.card.name != "Shiko Stomp":
            continue
        fighter.temporary_zone.remove(instance)
        fighter.discard_pile.append(instance.card)
        state.log(
            f"Shiko Stomp prevents {source}: {description} "
            f"against {fighter.wrestler.name}."
        )
        return True
    return False
