from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .models import BoutState, Card, GripState, Side, Stat
from .prevention import prevent_negative_effect
from .rules import (
    establish_grip,
    gain_momentum,
    gain_position,
    gain_power,
    gain_push,
    improve_grip,
    lose_momentum,
    lose_position,
    lose_power,
    reduce_grip,
)
from .selection import ai_look_keep
from .tachiai import TachiaiComparison
from .temporary import add_temporary


class IllegalPlay(RuntimeError):
    pass


class ChoiceRequired(RuntimeError):
    def __init__(self, card_name: str, choice_name: str, options: list[Any]) -> None:
        self.card_name = card_name
        self.choice_name = choice_name
        self.options = options
        super().__init__(
            f"{card_name} requires choice {choice_name!r}: "
            + ", ".join(str(option) for option in options)
        )


class DeckEmptyDuringDraw(RuntimeError):
    pass


@dataclass(frozen=True)
class EffectContext:
    comparison: TachiaiComparison | None = None
    choices: dict[str, Any] | None = None

    def choice(self, name: str) -> Any | None:
        if self.choices is None:
            return None
        return self.choices.get(name)


ExchangeEffect = Callable[[BoutState, Side, Card, EffectContext], None]


def draw_one(state: BoutState, side: Side) -> Card:
    fighter = state.fighter(side)
    if not fighter.draw_pile:
        raise DeckEmptyDuringDraw(
            f"{fighter.wrestler.name} attempted to draw from an empty Draw Pile."
        )
    card = fighter.draw_pile.pop(0)
    fighter.hand.append(card)
    state.log(f"{fighter.wrestler.name} draws {card.name}.")
    return card


def add_play(state: BoutState, side: Side, amount: int = 1) -> None:
    state.fighter(side).plays_remaining += amount
    state.log(f"{state.fighter(side).wrestler.name} gains {amount} Play.")


def tachiai_advantage(context: EffectContext, side: Side, stat: Stat) -> int:
    if context.comparison is None:
        raise ValueError("This effect requires the Tachiai comparison.")
    return context.comparison.advantage_for(side, stat)


def tachiai_comparisons_won(context: EffectContext, side: Side) -> int:
    if context.comparison is None:
        raise ValueError("This effect requires the Tachiai comparison.")
    return sum(
        1
        for stat in (Stat.POWER, Stat.TECHNIQUE, Stat.SPIRIT)
        if context.comparison.advantage_for(side, stat) > 0
    )


def _oshi(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    gain_push(state, side, 1)
    add_play(state, side)
    draw_one(state, side)


def _tsuki(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    add_play(state, side)
    opponent = state.opponent(side)
    available: list[str] = []
    if opponent.left_grip is not GripState.NONE:
        available.append("left")
    if opponent.right_grip is not GripState.NONE:
        available.append("right")

    chosen: str | None = None
    if len(available) == 1:
        chosen = available[0]
    elif len(available) > 1:
        chosen = context.choice("grip")
        if chosen not in available:
            raise ChoiceRequired(card.name, "grip", available)

    if chosen is not None and not prevent_negative_effect(
        state,
        state.opponent_side(side),
        source="Tsuki",
        description=f"reduce {chosen.title()} Grip",
    ):
        reduce_grip(state, state.opponent_side(side), hand=chosen)

    draw_one(state, side)


def _tsuppari(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    fighter = state.fighter(side)
    chained = any(
        played.name in {"Oshi", "Tsuki", "Tsuppari"}
        for played in fighter.played_this_turn[:-1]
    )
    gain_momentum(state, side, 1)
    if chained:
        gain_push(state, side, 1)
    add_play(state, side)
    draw_one(state, side)


def _harite(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    gain_power(state, side, 1)
    opponent_side = state.opponent_side(side)
    if not prevent_negative_effect(
        state,
        opponent_side,
        source="Harite",
        description="lose 1 Power",
    ):
        lose_power(state, opponent_side, 1)


def _gain_left_grip(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    fighter = state.fighter(side)
    if fighter.left_grip is GripState.NONE:
        establish_grip(state, side, "left")
    else:
        gain_momentum(state, side, 1)


def _gain_right_grip(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    fighter = state.fighter(side)
    if fighter.right_grip is GripState.NONE:
        establish_grip(state, side, "right")
    else:
        gain_push(state, side, 1)


def _uwate(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    fighter = state.fighter(side)
    if fighter.left_grip is GripState.DEEP:
        gain_momentum(state, side, 2)
    else:
        improve_grip(state, side, "left")


def _shitate(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    fighter = state.fighter(side)
    if fighter.right_grip is GripState.DEEP:
        gain_push(state, side, 2)
    else:
        improve_grip(state, side, "right")


def _salt_throw(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    draw_one(state, side)
    if tachiai_advantage(context, side, Stat.SPIRIT) >= 3:
        gain_momentum(state, side, 1)


def _stare_down(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    look = 1 + tachiai_comparisons_won(context, side)
    ai_look_keep(state.fighter(side), look, 1)


def _belt_slap(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    gain_push(state, side, 1)
    if tachiai_advantage(context, side, Stat.SPIRIT) >= 3:
        gain_momentum(state, side, 1)


def _tsuri(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    grip = state.fighter(side).total_grip
    if grip == 1:
        gain_push(state, side, 1)
    elif grip == 2:
        gain_push(state, side, 2)
    elif grip == 3:
        gain_push(state, side, 3)
    elif grip >= 4:
        gain_push(state, side, 3)
        gain_momentum(state, side, 1)


def _yori(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    if state.fighter(side).total_grip < 1:
        raise IllegalPlay("Yori requires at least 1 Grip.")
    position = state.position * state.sign(side)
    if position > 0:
        gain_momentum(state, side, min(position, 3))


def _gaburi(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    if state.fighter(side).total_grip < 1:
        raise IllegalPlay("Gaburi requires at least 1 Grip.")
    momentum = state.momentum * state.sign(side)
    if momentum > 0:
        gain_push(state, side, min(momentum, 3))


def _henka(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    draw_one(state, side)


def _reset_to_neutral(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    fighter = state.fighter(side)
    removed = fighter.total_grip > 0
    fighter.left_grip = GripState.NONE
    fighter.right_grip = GripState.NONE

    if state.momentum * state.sign(side) < 0:
        state.momentum = 0
        state.log(f"{fighter.wrestler.name} resets Momentum to 0.")

    if removed:
        gain_position(state, side, 1)


def _regain_balance(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    if state.momentum * state.sign(side) < 0:
        gain_momentum(state, side, 2)
    else:
        draw_one(state, side)


def _give_ground(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    gain_momentum(state, side, 1)
    lose_position(state, side, 1)
    ai_look_keep(state.fighter(side), 2, 1)



def _headlong_charge(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    gain_momentum(state, side, 1)
    gain_push(state, side, 1)
    gain_power(state, side, 1)
    add_temporary(state, side, card, phase="exchange")


def _attempt_two_handed(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    add_temporary(state, side, card, phase="exchange")


def _attempt_deep_outside(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    add_temporary(state, side, card, phase="exchange")


def _attempt_deep_inside(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    add_temporary(state, side, card, phase="exchange")


def _hold_position(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    add_temporary(state, side, card, phase="exchange")


def _immovable(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    gain_power(state, side, 1)
    add_temporary(state, side, card, phase="exchange")


def _get_underneath(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    gain_momentum(state, side, 1)
    gain_push(state, side, 1)
    add_temporary(state, side, card, phase="exchange")


def _use_the_tawara(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    use_cost = context.choice("lose_position_for_power")
    if use_cost is None:
        raise ChoiceRequired(card.name, "lose_position_for_power", [True, False])
    if use_cost:
        lose_position(state, side, 1)
        gain_power(state, side, 1)
    add_temporary(state, side, card, phase="exchange")


def _kannuki(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    add_temporary(state, side, card, phase="exchange")

EXCHANGE_EFFECTS: dict[str, ExchangeEffect] = {
    "Oshi": _oshi,
    "Tsuki": _tsuki,
    "Tsuppari": _tsuppari,
    "Harite": _harite,
    "Headlong Charge": _headlong_charge,
    "Gain Left Grip": _gain_left_grip,
    "Gain Right Grip": _gain_right_grip,
    "Uwate": _uwate,
    "Shitate": _shitate,
    "Attempt Two-Handed Grip": _attempt_two_handed,
    "Attempt Deep Outside Grip": _attempt_deep_outside,
    "Attempt Deep Inside Grip": _attempt_deep_inside,
    "Salt Throw": _salt_throw,
    "Stare Down": _stare_down,
    "Belt Slap": _belt_slap,
    "Tsuri": _tsuri,
    "Yori": _yori,
    "Gaburi": _gaburi,
    "Hold Position": _hold_position,
    "Immovable": _immovable,
    "Henka": _henka,
    "Reset to Neutral": _reset_to_neutral,
    "Get Underneath": _get_underneath,
    "Regain Balance": _regain_balance,
    "Use the Tawara": _use_the_tawara,
    "Kannuki": _kannuki,
    "Give Ground": _give_ground,
}


TEMPORARY_CARD_NAMES: frozenset[str] = frozenset(
    {
        "Headlong Charge",
        "Attempt Two-Handed Grip",
        "Attempt Deep Outside Grip",
        "Attempt Deep Inside Grip",
        "Hold Position",
        "Immovable",
        "Pull",
        "Get Underneath",
        "Sidestep",
        "Use the Tawara",
        "Kannuki",
        "Morozashi",
    }
)

UNIMPLEMENTED_TEMPORARY_CARD_NAMES: frozenset[str] = frozenset(
    {
        "Pull",
        "Sidestep",
        "Morozashi",
    }
)

CHOICE_OR_TEMPORARY_EFFECTS_NOT_YET_REGISTERED: frozenset[str] = frozenset(
    {
        "Nodowa",
        "Power Water",
        "Ottsuke",
        "Read the Move",
    }
)


def resolve_exchange_effect(
    state: BoutState,
    side: Side,
    card: Card,
    context: EffectContext,
) -> None:
    effect = EXCHANGE_EFFECTS.get(card.name)
    if effect is not None:
        effect(state, side, card, context)
        return

    if card.name in UNIMPLEMENTED_TEMPORARY_CARD_NAMES:
        raise NotImplementedError(
            f"Temporary effect for {card.name} is not implemented yet."
        )
    if card.name in CHOICE_OR_TEMPORARY_EFFECTS_NOT_YET_REGISTERED:
        raise NotImplementedError(
            f"Choice-dependent effect for {card.name} is not implemented yet."
        )

    raise KeyError(f"No Exchange effect registered for {card.name!r}.")
