from __future__ import annotations

from .models import BoutState, Card, GripState, Side
from .rules import effective_total_grip, grip_benefits_suppressed


def can_play_card(state: BoutState, side: Side, card: Card) -> bool:
    if state.winner is not None:
        return False

    fighter = state.fighter(side)
    if card not in fighter.hand or fighter.plays_remaining <= 0:
        return False

    # Kannuki prevents Grip-building cards from being committed to the board.
    # Blocking only their immediate Grip effect lets delayed attempts resolve
    # after Kannuki expires, which is not the intended counterplay.
    if grip_benefits_suppressed(state, side) and card.name in {
        "Gain Left Grip", "Gain Right Grip", "Uwate", "Shitate",
        "Attempt Two-Handed Grip", "Attempt Deep Outside Grip",
        "Attempt Deep Inside Grip", "Morozashi",
    }:
        return False

    if card.name == "Morozashi":
        return (
            (fighter.left_grip is GripState.GRIP and fighter.right_grip is GripState.NONE)
            or
            (fighter.right_grip is GripState.GRIP and fighter.left_grip is GripState.NONE)
        )

    if card.name == "Sidestep":
        return state.side_by_side_owner is None

    return True
