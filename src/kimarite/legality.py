from __future__ import annotations

from .models import BoutState, Card, GripState, Side
from .rules import effective_total_grip


def can_play_card(state: BoutState, side: Side, card: Card) -> bool:
    if state.winner is not None:
        return False

    fighter = state.fighter(side)
    if card not in fighter.hand or fighter.plays_remaining <= 0:
        return False

    if card.name in {"Yori", "Gaburi"}:
        return effective_total_grip(state, side) >= 1

    if card.name == "Morozashi":
        return (
            (fighter.left_grip is GripState.GRIP and fighter.right_grip is GripState.NONE)
            or
            (fighter.right_grip is GripState.GRIP and fighter.left_grip is GripState.NONE)
        )

    # Sidestep remains temporarily unavailable to the autonomous runner until
    # Push behavior during Side-by-Side is explicitly resolved.
    if card.name == "Sidestep":
        return False

    return True
