"""Tachiai orb comparison for B11 player-committed cards."""
from __future__ import annotations
from typing import Sequence
from .models import Card, Wrestler
from .tachiai import TachiaiComparison, TachiaiStats, prepared_stats


def player_tachiai_orbs(wrestler: Wrestler, cards: Sequence[Card]) -> TachiaiStats:
    """Human base stats, universal +1, and only the committed cards' orbs."""
    return TachiaiStats(
        wrestler.base_power + 1 + sum(c.power for c in cards),
        wrestler.base_technique + 1 + sum(c.technique for c in cards),
        wrestler.base_spirit + 1 + sum(c.spirit for c in cards),
    )


def compare_player_tachiai(
    human: Wrestler, opponent: Wrestler, committed: Sequence[Card]
) -> TachiaiComparison:
    """Keep AI's original preparation unchanged."""
    a = player_tachiai_orbs(human, committed)
    b = prepared_stats(opponent)
    return TachiaiComparison(
        wrestler_a=a,
        wrestler_b=b,
        power_advantage_a=a.power-b.power,
        technique_advantage_a=a.technique-b.technique,
        spirit_advantage_a=a.spirit-b.spirit,
    )
