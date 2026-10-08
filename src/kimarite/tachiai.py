from __future__ import annotations

from dataclasses import dataclass

from .models import Card, Wrestler


@dataclass(frozen=True)
class TachiaiStats:
    power: int
    technique: int
    spirit: int


@dataclass(frozen=True)
class TachiaiComparison:
    wrestler_a: TachiaiStats
    wrestler_b: TachiaiStats
    power_advantage_a: int
    technique_advantage_a: int
    spirit_advantage_a: int


def prepared_stats(wrestler: Wrestler) -> TachiaiStats:
    cards: tuple[Card, Card] = (
        wrestler.starting_kimarite,
        wrestler.prepared_tachiai_card,
    )
    return TachiaiStats(
        power=wrestler.base_power + sum(card.power for card in cards),
        technique=wrestler.base_technique + sum(card.technique for card in cards),
        spirit=wrestler.base_spirit + sum(card.spirit for card in cards),
    )


def compare_tachiai(wrestler_a: Wrestler, wrestler_b: Wrestler) -> TachiaiComparison:
    a = prepared_stats(wrestler_a)
    b = prepared_stats(wrestler_b)
    return TachiaiComparison(
        wrestler_a=a,
        wrestler_b=b,
        power_advantage_a=a.power - b.power,
        technique_advantage_a=a.technique - b.technique,
        spirit_advantage_a=a.spirit - b.spirit,
    )
