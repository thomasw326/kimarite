"""B11 multi-commit Oshi/Tsuki reveal-chain planning.

Each committed Oshi or Tsuki starts its own reveal chain. Every card
revealed contributes its printed orbs, including the non-family card
that terminates the chain. Cards are removed from the draw pile in
order, making the behaviour deterministic for a given deck seed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .models import Card

REVEAL_FAMILY = frozenset(("Oshi", "Tsuki"))


@dataclass(frozen=True)
class TachiaiReveals:
    revealed: tuple[Card, ...]
    remaining: tuple[Card, ...]
    orbs: tuple[int, int, int]


def plan_reveals(committed: Sequence[Card], draw_pile: Sequence[Card]) -> TachiaiReveals:
    """Evaluate all committed reveal cards without mutating the live state."""
    remaining = list(draw_pile)
    revealed: list[Card] = []
    for played in committed:
        if played.name not in REVEAL_FAMILY:
            continue
        while remaining:
            card = remaining.pop(0)
            revealed.append(card)
            if card.name not in REVEAL_FAMILY:
                break
    return TachiaiReveals(
        revealed=tuple(revealed),
        remaining=tuple(remaining),
        orbs=(
            sum(card.power for card in revealed),
            sum(card.technique for card in revealed),
            sum(card.spirit for card in revealed),
        ),
    )
