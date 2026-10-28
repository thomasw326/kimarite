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
    return (effective_total_grip(state, side) >= 1 and relative_momentum(state, side) >= 1 and relative_position(state, side) >= 2)


def _oshidashi(state: BoutState, side: Side) -> bool:
    return relative_position(state, side) >= 2 and relative_momentum(state, side) >= 2


def _tsukidashi(state: BoutState, side: Side) -> bool:
    return relative_position(state, side) >= 3 and state.fighter(side).cards_played_this_turn >= 3


def _oshitaoshi(state: BoutState, side: Side) -> bool:
    return (
        relative_momentum(state, side) >= 2
        and relative_position(state, side) >= 1
        and state.fighter(side).power >= 8
    )


def _yoritaoshi(state: BoutState, side: Side) -> bool:
    return (effective_total_grip(state, side) >= 1 and relative_position(state, side) >= 2 and power_advantage(state, side) >= 2)


def _katasukashi(state: BoutState, side: Side) -> bool:
    return (no_grip(state, state.opponent_side(side)) and relative_momentum(state, side) >= 2 and len(state.fighter(side).hand) - len(state.opponent(side).hand) >= 4)


def _tsukiotoshi(state: BoutState, side: Side) -> bool:
    return (no_grip(state, side) and relative_momentum(state, side) >= 1 and power_advantage(state, side) <= -3
            and state.opponent(side).unstable)


def _tottari(state: BoutState, side: Side) -> bool:
    return (
        no_grip(state, side)
        and state.fighter(side).opponent_grip_reduced_this_turn
        and len(state.opponent(side).discard_pile) >= 7
    )


def _uwatenage(state: BoutState, side: Side) -> bool:
    return (
        has_deep_left(state, side)
        and relative_momentum(state, side) >= 1
        and relative_position(state, side) >= 0
    )


def _shitatenage(state: BoutState, side: Side) -> bool:
    return (
        effective_total_grip(state, side) > 0
        and state.fighter(side).right_grip is GripState.DEEP
        and relative_momentum(state, side) >= 1
        and relative_position(state, side) >= 0
    )


def _hatakikomi(state: BoutState, side: Side) -> bool:
    return (relative_momentum(state, side) <= -2
            and state.fighter(side).power >= 6
            and state.opponent(side).unstable)


def _hikiotoshi(state: BoutState, side: Side) -> bool:
    return (
        relative_momentum(state, side) <= -2
        and relative_position(state, side) >= 0
        and has_any_grip(state, side)
    )


def _tsukitaoshi(state: BoutState, side: Side) -> bool:
    return state.fighter(side).cards_played_this_turn >= 4


def _tsuridashi(state: BoutState, side: Side) -> bool:
    return (effective_total_grip(state, side) >= 3 and relative_position(state, side) >= 0 and state.fighter(side).power >= 6)


def _kotenage(state: BoutState, side: Side) -> bool:
    return (
        effective_total_grip(state, state.opponent_side(side)) == 0
        and relative_momentum(state, side) >= 1
        and len(state.fighter(side).hand) >= 5
    )


def _abisetaoshi(state: BoutState, side: Side) -> bool:
    return (effective_total_grip(state, side) >= 2
            and state.fighter(side).power >= 10
            and relative_momentum(state, side) >= 1)


def _kirikaeshi(state: BoutState, side: Side) -> bool:
    f = state.fighter(side)
    return (power_advantage(state, side) <= -3 and not f.unstable
            and state.opponent(side).unstable and relative_momentum(state, side) >= 2)


def _okuridashi(state: BoutState, side: Side) -> bool:
    # B9 generated-only finisher: mirrors Oshidashi with one less Momentum.
    return relative_position(state, side) >= 2 and relative_momentum(state, side) >= 1


def _okuritaoshi(state: BoutState, side: Side) -> bool:
    # B9 generated-only finisher: mirrors Oshitaoshi with one less Momentum.
    return state.fighter(side).power >= 8 and relative_momentum(state, side) >= 1


def _tsuriotoshi(state: BoutState, side: Side) -> bool:
    fighter = state.fighter(side)
    return fighter.power + relative_momentum(state, side) + effective_total_grip(state, side) >= 15


def _sukuinage(state: BoutState, side: Side) -> bool:
    return (no_grip(state, side) and relative_momentum(state, side) >= 2
            and len(state.fighter(side).hand) - len(state.opponent(side).hand) >= 4)


def _utchari(state: BoutState, side: Side) -> bool:
    return state.fighter(side).gained_momentum_this_turn and relative_position(state, side) <= -3


def _uwatedashinage(state: BoutState, side: Side) -> bool:
    return (state.fighter(side).left_grip is not GripState.NONE
            and effective_total_grip(state, side) > 0
            and relative_momentum(state, side) >= 1
            and power_advantage(state, side) <= -5)


KIMARITE_PREDICATES: dict[str, Predicate] = {
    "Uwatedashinage": _uwatedashinage,
    "Utchari": _utchari,
    "Sukuinage": _sukuinage,
    "Tsuriotoshi": _tsuriotoshi,
    "Okuritaoshi": _okuritaoshi,
    "Okuridashi": _okuridashi,
    "Kirikaeshi": _kirikaeshi,
    "Yorikiri": _yorikiri,
    "Oshidashi": _oshidashi,
    "Tsukidashi": _tsukidashi,
    "Oshitaoshi": _oshitaoshi,
    "Yoritaoshi": _yoritaoshi,
    "Katasukashi": _katasukashi,
    "Tsukiotoshi": _tsukiotoshi,
    "Tottari": _tottari,
    "Uwatenage": _uwatenage,
    "Shitatenage": _shitatenage,
    "Hatakikomi": _hatakikomi,
    "Hikiotoshi": _hikiotoshi,
    "Tsukitaoshi": _tsukitaoshi,
    "Tsuridashi": _tsuridashi,
    "Kotenage": _kotenage,
    "Abisetaoshi": _abisetaoshi,
}


def kimarite_is_satisfied(state: BoutState, side: Side, card: Card) -> bool:
    # Experimental R20 arms are distinct cards, never an alias for the live rule.
    if card.name.startswith("R21:"):
        from .r21_variant_rules import arm_id, variant_predicate
        return variant_predicate(state, side, arm_id(card))
    if card.name.startswith("R20:"):
        from .r20_variant_rules import arm_id, variant_predicate
        return variant_predicate(state, side, arm_id(card))
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
