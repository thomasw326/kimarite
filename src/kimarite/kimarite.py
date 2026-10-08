from __future__ import annotations

from collections.abc import Callable

from .models import BoutState, Card, GripState, Side
from .rules import effective_total_grip


Predicate = Callable[[BoutState, Side], bool]


def relative_momentum(state: BoutState, side: Side) -> int:
    return state.momentum * state.sign(side)


def relative_position(state: BoutState, side: Side) -> int:
    return state.position * state.sign(side)


def power_advantage(state: BoutState, side: Side) -> int:
    return state.fighter(side).power - state.opponent(side).power


def has_any_grip(state: BoutState, side: Side) -> bool:
    return effective_total_grip(state, side) > 0


def has_both_grips(state: BoutState, side: Side) -> bool:
    if effective_total_grip(state, side) == 0:
        return False
    fighter = state.fighter(side)
    return (
        fighter.left_grip is not GripState.NONE
        and fighter.right_grip is not GripState.NONE
    )


def has_deep_left(state: BoutState, side: Side) -> bool:
    return (
        effective_total_grip(state, side) > 0
        and state.fighter(side).left_grip is GripState.DEEP
    )


def no_grip(state: BoutState, side: Side) -> bool:
    return state.fighter(side).total_grip == 0


def _yorikiri(state: BoutState, side: Side) -> bool:
    return (
        effective_total_grip(state, side) >= 2
        and relative_momentum(state, side) >= 1
        and relative_position(state, side) >= 2
    )


def _oshidashi(state: BoutState, side: Side) -> bool:
    return (
        power_advantage(state, side) >= 3
        and relative_momentum(state, side) >= 1
        and relative_position(state, side) >= 2
    )


def _tsukidashi(state: BoutState, side: Side) -> bool:
    return (
        relative_momentum(state, side) >= 0
        and relative_position(state, side) >= 2
        and state.fighter(side).cards_played_this_turn >= 4
    )


def _oshitaoshi(state: BoutState, side: Side) -> bool:
    return (
        relative_momentum(state, side) >= 1
        and relative_position(state, side) >= 1
        and state.fighter(side).power >= 8
    )


def _yoritaoshi(state: BoutState, side: Side) -> bool:
    return (
        effective_total_grip(state, side) >= 2
        and relative_position(state, side) >= 2
        and power_advantage(state, side) >= 3
    )


def _katasukashi(state: BoutState, side: Side) -> bool:
    return (
        no_grip(state, side)
        and relative_position(state, side) >= 0
        and state.fighter(side).lost_position_this_turn
    )


def _tsukiotoshi(state: BoutState, side: Side) -> bool:
    fighter = state.fighter(side)
    opponent = state.opponent(side)
    return (
        relative_position(state, side) <= -2
        and len(opponent.discard_pile) >= len(fighter.discard_pile) + 3
    )


def _tottari(state: BoutState, side: Side) -> bool:
    return (
        no_grip(state, side)
        and state.fighter(side).opponent_grip_reduced_this_turn
        and relative_momentum(state, side) >= 2
    )


def _uwatenage(state: BoutState, side: Side) -> bool:
    return (
        has_deep_left(state, side)
        and relative_momentum(state, side) >= 1
        and relative_position(state, side) >= 0
    )


def _hatakikomi(state: BoutState, side: Side) -> bool:
    return (
        relative_momentum(state, side) <= -2
        and relative_position(state, side) >= 0
        and state.fighter(side).power >= 5
    )


def _hikiotoshi(state: BoutState, side: Side) -> bool:
    return (
        relative_momentum(state, side) <= -2
        and relative_position(state, side) >= 0
        and has_any_grip(state, side)
    )


def _tsukitaoshi(state: BoutState, side: Side) -> bool:
    return (
        relative_momentum(state, side) >= 2
        and relative_position(state, side) >= 0
        and state.fighter(side).cards_played_this_turn >= 4
    )


def _tsuridashi(state: BoutState, side: Side) -> bool:
    return has_both_grips(state, side) and state.fighter(side).power >= 7


def _kotenage(state: BoutState, side: Side) -> bool:
    return (
        effective_total_grip(state, state.opponent_side(side)) == 0
        and relative_momentum(state, side) >= 1
        and len(state.fighter(side).hand) >= 3
    )


def _abisetaoshi(state: BoutState, side: Side) -> bool:
    return (
        effective_total_grip(state, side) >= 2
        and relative_momentum(state, side) >= 1
        and state.fighter(side).power >= 7
    )


KIMARITE_PREDICATES: dict[str, Predicate] = {
    "Yorikiri": _yorikiri,
    "Oshidashi": _oshidashi,
    "Tsukidashi": _tsukidashi,
    "Oshitaoshi": _oshitaoshi,
    "Yoritaoshi": _yoritaoshi,
    "Katasukashi": _katasukashi,
    "Tsukiotoshi": _tsukiotoshi,
    "Tottari": _tottari,
    "Uwatenage": _uwatenage,
    "Hatakikomi": _hatakikomi,
    "Hikiotoshi": _hikiotoshi,
    "Tsukitaoshi": _tsukitaoshi,
    "Tsuridashi": _tsuridashi,
    "Kotenage": _kotenage,
    "Abisetaoshi": _abisetaoshi,
}


def kimarite_is_satisfied(state: BoutState, side: Side, card: Card) -> bool:
    predicate = KIMARITE_PREDICATES.get(card.name)
    if predicate is None:
        raise KeyError(f"No Kimarite predicate registered for {card.name!r}")
    return predicate(state, side)


def satisfied_kimarite(state: BoutState, side: Side) -> list[Card]:
    return [
        card
        for card in state.fighter(side).kimarite_zone
        if kimarite_is_satisfied(state, side, card)
    ]
