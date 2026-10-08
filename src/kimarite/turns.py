from __future__ import annotations

from collections.abc import Callable

from .kimarite import satisfied_kimarite
from .models import BoutState, Card, Side, Stat
from .rules import gain_momentum
from .selection import ai_look_keep
from .tachiai import TachiaiComparison, spirit_rewards, technique_access


class TemporaryResolutionRequired(RuntimeError):
    pass


TemporaryStartResolver = Callable[[BoutState, Side], None]
KimariteChoiceResolver = Callable[[BoutState, Side, list[Card]], Card]


def prepare_exchange_deck(state: BoutState, side: Side) -> None:
    """Put the prepared Tachiai card on the bottom after Tachiai resolution."""
    fighter = state.fighter(side)
    fighter.draw_pile.append(fighter.wrestler.prepared_tachiai_card)


def apply_initial_power(state: BoutState, comparison: TachiaiComparison) -> None:
    """Power persists into the Exchange at the prepared Tachiai total."""
    state.fighter_a.power = comparison.wrestler_a.power
    state.fighter_b.power = comparison.wrestler_b.power


def resolve_first_turn_spirit_reward(
    state: BoutState,
    side: Side,
    comparison: TachiaiComparison,
) -> tuple[int, int]:
    """Resolve first-turn Spirit before the start-of-turn Kimarite check."""
    fighter = state.fighter(side)
    if not fighter.spirit_reward_pending:
        return (0, 0)

    advantage = comparison.advantage_for(side, Stat.SPIRIT)
    momentum, bonus_turns = spirit_rewards(advantage)
    fighter.spirit_reward_pending = False
    fighter.bonus_turns_queued += bonus_turns
    if momentum:
        gain_momentum(state, side, momentum)
    return (momentum, bonus_turns)


def first_turn_card_access(
    state: BoutState,
    side: Side,
    comparison: TachiaiComparison,
) -> list[Card]:
    fighter = state.fighter(side)
    if not fighter.technique_reward_pending:
        return []

    # The first-turn Technique result IS the first hand/card access for that turn.
    # It does not stack with the ordinary 2 + Grip Exchange selection.
    advantage = comparison.advantage_for(side, Stat.TECHNIQUE)
    look, keep = technique_access(advantage)
    fighter.technique_reward_pending = False
    return ai_look_keep(fighter, look, keep)


def normal_turn_card_access(state: BoutState, side: Side) -> list[Card]:
    fighter = state.fighter(side)
    look = 2 + fighter.total_grip
    return ai_look_keep(fighter, look, 2)


def resolve_turn_card_access(
    state: BoutState,
    side: Side,
    comparison: TachiaiComparison,
) -> list[Card]:
    fighter = state.fighter(side)
    if fighter.first_exchange_turn:
        cards = first_turn_card_access(state, side, comparison)
        fighter.first_exchange_turn = False
        return cards
    return normal_turn_card_access(state, side)


def apply_start_of_turn_exhaustion(state: BoutState, side: Side) -> None:
    """Apply the current start-of-turn Exhaustion rule once for this turn."""
    fighter = state.fighter(side)

    if not fighter.draw_pile:
        state.declare_winner(state.opponent_side(side), "Exhaustion")
        return

    if len(fighter.discard_pile) >= 10:
        fighter.power -= 1
        state.log(f"{fighter.wrestler.name} loses 1 Power to Exhaustion.")

    if fighter.power < 0:
        state.declare_winner(state.opponent_side(side), "Power")


def reset_turn_events(state: BoutState, side: Side) -> None:
    fighter = state.fighter(side)
    fighter.plays_remaining = 2
    fighter.cards_played_this_turn = 0
    fighter.lost_position_this_turn = False
    fighter.opponent_grip_reduced_this_turn = False
    fighter.gained_push_this_turn = False
    fighter.gained_momentum_this_turn = False


def check_kimarite_zone(
    state: BoutState,
    side: Side,
    *,
    choose_kimarite: KimariteChoiceResolver | None = None,
) -> Card | None:
    """Resolve a Kimarite win.

    Satisfied cards are returned in Kimarite Zone order, so the default is the
    earliest-played satisfied Kimarite. A chooser may override that selection
    when a later reward layer determines the alternatives have meaningfully
    different win rewards.
    """
    cards = satisfied_kimarite(state, side)
    if not cards:
        return None

    if choose_kimarite is None or len(cards) == 1:
        card = cards[0]
    else:
        card = choose_kimarite(state, side, cards)
        if card not in cards:
            raise ValueError("Kimarite chooser must return one of the satisfied cards.")

    state.declare_winner(side, card.name)
    return card


def start_exchange_turn(
    state: BoutState,
    side: Side,
    comparison: TachiaiComparison,
    *,
    resolve_temporary_start: TemporaryStartResolver | None = None,
    choose_kimarite: KimariteChoiceResolver | None = None,
) -> list[Card]:
    """Run the fixed start-of-turn sequence through card access.

    Order:
    1. reset turn counters/events
    2. first-turn Spirit reward (first Exchange turn only)
    3. start-of-turn Kimarite check
    4. start-of-turn Temporary effects
    5. Exhaustion / negative-Power loss
    6. first-turn Technique access OR normal 2 + Grip access

    Temporary-zone behavior is card-specific, so a resolver is required when
    cards are present rather than silently guessing duration/resolution.
    """
    state.active_side = side
    state.turn_number += 1
    reset_turn_events(state, side)

    fighter = state.fighter(side)
    if fighter.first_exchange_turn:
        resolve_first_turn_spirit_reward(state, side, comparison)
        if state.winner is not None:
            return []

    check_kimarite_zone(state, side, choose_kimarite=choose_kimarite)
    if state.winner is not None:
        return []

    if fighter.temporary_zone:
        if resolve_temporary_start is None:
            raise TemporaryResolutionRequired(
                f"{fighter.wrestler.name} has Temporary cards requiring start resolution."
            )
        resolve_temporary_start(state, side)
        if state.winner is not None:
            return []

    apply_start_of_turn_exhaustion(state, side)
    if state.winner is not None:
        return []

    return resolve_turn_card_access(state, side, comparison)


def end_exchange_turn(
    state: BoutState,
    side: Side,
    *,
    choose_kimarite: KimariteChoiceResolver | None = None,
) -> Side | None:
    """Check Kimarite, then schedule the next wrestler."""
    check_kimarite_zone(state, side, choose_kimarite=choose_kimarite)
    if state.winner is not None:
        return None

    fighter = state.fighter(side)
    if fighter.bonus_turns_queued > 0:
        fighter.bonus_turns_queued -= 1
        next_side = side
    else:
        next_side = state.opponent_side(side)

    state.active_side = next_side
    return next_side
