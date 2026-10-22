from __future__ import annotations

from dataclasses import dataclass

from .models import BoutState, Card, Side, Stat, Wrestler


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

    @property
    def power_winner(self) -> Side | None:
        return _winner_from_signed(self.power_advantage_a)

    @property
    def technique_winner(self) -> Side | None:
        return _winner_from_signed(self.technique_advantage_a)

    @property
    def spirit_winner(self) -> Side | None:
        return _winner_from_signed(self.spirit_advantage_a)

    def advantage_for(self, side: Side, stat: Stat) -> int:
        value = {
            Stat.POWER: self.power_advantage_a,
            Stat.TECHNIQUE: self.technique_advantage_a,
            Stat.SPIRIT: self.spirit_advantage_a,
        }[stat]
        return value if side is Side.A else -value


def _winner_from_signed(value: int) -> Side | None:
    if value > 0:
        return Side.A
    if value < 0:
        return Side.B
    return None


def prepared_stats(wrestler: Wrestler) -> TachiaiStats:
    cards: tuple[Card, Card] = (
        wrestler.starting_kimarite,
        wrestler.prepared_tachiai_card,
    )
    return TachiaiStats(
        power=wrestler.base_power + 1 + sum(card.power for card in cards),
        technique=wrestler.base_technique + 1 + sum(card.technique for card in cards),
        spirit=wrestler.base_spirit + 1 + sum(card.spirit for card in cards),
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


def push_from_power_advantage(advantage: int) -> int:
    """Spirit Push thresholds: 1, 4, 7, 10, 13..."""
    if advantage <= 0:
        return 0
    return 1 + (advantage - 1) // 3


def technique_thresholds(advantage: int) -> int:
    """Count Power defense thresholds at 1, 4, 7, 10, 13..."""
    return 0 if advantage <= 0 else 1 + (advantage - 1) // 3


def technique_access(advantage: int) -> tuple[int, int]:
    """Look improves per advantage; extra kept cards unlock at 1, 4, 7, 10, 13..."""
    if advantage <= 0:
        return (2, 2)
    keep = 2 + technique_thresholds(advantage)
    return (keep, keep)


def spirit_rewards(advantage: int) -> tuple[int, int]:
    """Return (first-turn Momentum, bonus consecutive Exchange turns)."""
    if advantage <= 0:
        return (0, 0)
    momentum = 1 if advantage >= 3 else 0
    bonus_turns = 1 if advantage >= 6 else 0
    return (momentum, bonus_turns)


def first_exchange_side(
    comparison: TachiaiComparison,
    wrestler_a: Wrestler,
    wrestler_b: Wrestler,
) -> Side:
    """Resolve Technique, then Spirit, Power, then ranking."""
    for value in (
        comparison.technique_advantage_a,
        comparison.spirit_advantage_a,
        comparison.power_advantage_a,
    ):
        winner = _winner_from_signed(value)
        if winner is not None:
            return winner

    if wrestler_a.ranking is not None and wrestler_b.ranking is not None:
        return Side.A if wrestler_a.ranking < wrestler_b.ranking else Side.B

    raise ValueError("Tachiai priority is tied and wrestler ranking is unavailable.")


def apply_tachiai_push(
    state: BoutState,
    side: Side,
    amount: int,
) -> int:
    """Apply Tachiai Push with immediate force-out beyond the edge."""
    if amount <= 0 or state.winner is not None:
        return 0

    target = state.position + state.sign(side) * amount
    if target > 3 or target < -3:
        state.position = 3 if side is Side.A else -3
        method = "Yorikiri" if state.fighter(side).total_grip > 0 else "Oshidashi"
        state.win_source = "ringout"
        state.declare_winner(side, method)
        return amount

    state.position = target
    state.log(f"{state.fighter(side).wrestler.name} gains {amount} Tachiai Push.")
    return amount


def apply_tachiai_power_push(
    state: BoutState,
    comparison: TachiaiComparison,
    *,
    reduction: int = 0,
) -> tuple[Side | None, int]:
    """Apply fixed Spirit-comparison Push reduced by Power defense.

    Tachiai force-out is special: Push beyond the ring edge ends the bout
    immediately instead of converting excess Push into Momentum.
    Card-specific Tachiai effects are resolved separately.
    """
    winner = comparison.spirit_winner
    if winner is None:
        return (None, 0)

    advantage = abs(comparison.spirit_advantage_a)
    defender = state.opponent_side(winner)
    # Prepared-card orbs are already included in the comparison.
    # Fighter Power changes are applied separately during Tachiai.
    base_advantage = comparison.advantage_for(defender, Stat.POWER)
    defender_delta = state.fighter(defender).power
    winner_delta = state.fighter(winner).power
    resistance = technique_thresholds(
        base_advantage + defender_delta - winner_delta
    )
    push = max(0, push_from_power_advantage(advantage) - resistance - max(0, reduction))
    apply_tachiai_push(state, winner, push)
    return (winner, push)
