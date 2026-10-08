from __future__ import annotations

from .models import BoutState, Side
from .selection import ai_look_keep
from .tachiai import TachiaiComparison, spirit_rewards, technique_access


def prepare_exchange_deck(state: BoutState, side: Side) -> None:
    """Put the prepared Tachiai card on the bottom after Tachiai resolution."""
    fighter = state.fighter(side)
    prepared = fighter.wrestler.prepared_tachiai_card
    if prepared not in fighter.draw_pile:
        fighter.draw_pile.append(prepared)


def apply_initial_power(state: BoutState, comparison: TachiaiComparison) -> None:
    state.fighter_a.power = comparison.wrestler_a.power
    state.fighter_b.power = comparison.wrestler_b.power


def resolve_first_turn_spirit_reward(
    state: BoutState,
    side: Side,
    comparison: TachiaiComparison,
) -> tuple[int, int]:
    fighter = state.fighter(side)
    if not fighter.spirit_reward_pending:
        return (0, 0)

    advantage = comparison.advantage_for(side, fighter.wrestler.primary.__class__.SPIRIT)
    momentum, bonus_turns = spirit_rewards(advantage)
    fighter.spirit_reward_pending = False
    fighter.bonus_turns_queued += bonus_turns
    return (momentum, bonus_turns)


def first_turn_card_access(
    state: BoutState,
    side: Side,
    comparison: TachiaiComparison,
) -> list:
    fighter = state.fighter(side)
    if not fighter.technique_reward_pending:
        return []

    # The first-turn Technique result IS the first hand/card access for that turn.
    # It does not stack with the ordinary 2 + Grip Exchange selection.
    advantage = comparison.advantage_for(side, fighter.wrestler.primary.__class__.TECHNIQUE)
    look, keep = technique_access(advantage)
    fighter.technique_reward_pending = False
    return ai_look_keep(fighter, look, keep)


def normal_turn_card_access(state: BoutState, side: Side) -> list:
    fighter = state.fighter(side)
    look = 2 + fighter.total_grip
    return ai_look_keep(fighter, look, 2)


def resolve_turn_card_access(
    state: BoutState,
    side: Side,
    comparison: TachiaiComparison,
) -> list:
    fighter = state.fighter(side)
    if fighter.first_exchange_turn:
        cards = first_turn_card_access(state, side, comparison)
        fighter.first_exchange_turn = False
        return cards
    return normal_turn_card_access(state, side)


def apply_start_of_turn_exhaustion(state: BoutState, side: Side) -> None:
    fighter = state.fighter(side)

    if not fighter.draw_pile:
        state.declare_winner(state.opponent_side(side), "Exhaustion")
        return

    if len(fighter.discard_pile) >= 10:
        fighter.power -= 1
        state.log(f"{fighter.wrestler.name} loses 1 Power to Exhaustion.")

    if fighter.power < 0:
        state.declare_winner(state.opponent_side(side), "Power")
