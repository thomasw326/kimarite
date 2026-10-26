"""Immutable B11 human-opening resolution input, built from physical deck slots.

This computes card destinations and reveal-chain consumption before the live
effect resolver mutates a bout. It does not grant Push, resolve individual
prepared effects or advance AI turns.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .b11_player_opening import PlayerOpening
from .b11_tachiai_phase import TachiaiDecision
from .b11_tachiai_reveals import plan_reveals
from .models import Card


@dataclass(frozen=True)
class PreparedHumanTachiai:
    committed: tuple[Card, ...]
    retained_hand: tuple[Card, ...]
    revealed_discard: tuple[Card, ...]
    draw_pile: tuple[Card, ...]
    reveal_orbs: tuple[int, int, int]


def prepare_human_tachiai(
    opening: PlayerOpening,
    decision: TachiaiDecision,
    actual_deck: Sequence[Card],
) -> PreparedHumanTachiai:
    """Consume each allocated copy exactly once and plan Oshi/Tsuki reveals.

    A committed card is NOT placed in discard here: card-specific resolution
    determines its final destination, including Kimarite/Temporary exceptions.
    """
    remaining = decision.unallocated_deck(opening, actual_deck)
    revealed = plan_reveals(decision.committed, remaining)
    return PreparedHumanTachiai(
        committed=decision.committed,
        retained_hand=decision.retained,
        revealed_discard=revealed.revealed,
        draw_pile=revealed.remaining,
        reveal_orbs=revealed.orbs,
    )
