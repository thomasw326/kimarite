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
    """Historical stepped threshold helper; B12 Tachiai Power now blocks 1-for-1."""
    return 0 if advantage <= 0 else 1 + (advantage - 1) // 3


def technique_access(advantage: int) -> tuple[int, int]:
    """Draw-only experiment: extra kept cards at +3, +6, +9, +12..."""
    if advantage <= 0:
        return (2, 2)
    keep = 2 + advantage // 3
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
    extra_push: dict[Side, int] | None = None,
) -> tuple[Side | None, int]:
    """Resolve all opening Push together, then block it using Power.

    Opening order:
    1. Spirit advantage generates Push at thresholds 1/4/7/...
    2. Explicit anti-Spirit-Push effects reduce that Spirit contribution.
    3. Prepared card effects generate bonus Push; opposing Push is netted.
    4. The defending wrestler blocks 1 net Push per point of *effective*
       Power advantage, after Tachiai Power effects have been applied once.
    5. Apply the remaining Push once, including immediate force-outs.

    The caller must first initialise fighter Power from the Tachiai stats
    (apply_initial_power) and apply any Tachiai-specific Power modifiers.
    This avoids adding the same starting Power advantage twice.
    """
    signed_push = 0
    if comparison.spirit_winner is not None:
        spirit_push = max(
            0,
            push_from_power_advantage(abs(comparison.spirit_advantage_a))
            - max(0, reduction),
        )
        signed_push = spirit_push * state.sign(comparison.spirit_winner)

    bonuses = extra_push or {}
    signed_push += bonuses.get(Side.A, 0) - bonuses.get(Side.B, 0)
    if not signed_push:
        return (None, 0)

    attacker = Side.A if signed_push > 0 else Side.B
    defender = state.opponent_side(attacker)
    effective_power_lead = state.fighter(defender).power - state.fighter(attacker).power
    blocks = max(0, effective_power_lead)
    net_push = max(0, abs(signed_push) - blocks)
    apply_tachiai_push(state, attacker, net_push)
    return (attacker, net_push)
