from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .models import BoutState, Card, GripState, Side, Stat
from .prevention import prevent_negative_effect
from .rules import (
    effective_total_grip,
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
from .temporary import add_temporary, remove_temporary


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
    grip = effective_total_grip(state, side, consume_prevention=True)
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
    if effective_total_grip(state, side, consume_prevention=True) < 1:
        raise IllegalPlay("Yori requires at least 1 usable Grip.")
    position = state.position * state.sign(side)
    if position > 0:
        gain_momentum(state, side, min(position, 3))


def _gaburi(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    if effective_total_grip(state, side, consume_prevention=True) < 1:
        raise IllegalPlay("Gaburi requires at least 1 usable Grip.")
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


def _choose_opponent_temporary(
    state: BoutState,
    side: Side,
    card: Card,
    context: EffectContext,
):
    instances = state.opponent(side).temporary_zone
    if not instances:
        return None
    if len(instances) == 1:
        return instances[0]

    choice = context.choice("temporary_index")
    options = list(range(len(instances)))
    if choice not in options:
        raise ChoiceRequired(card.name, "temporary_index", options)
    return instances[choice]


def _nodowa(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    gain_power(state, side, 2)
    target = _choose_opponent_temporary(state, side, card, context)
    if target is None:
        return

    opponent_side = state.opponent_side(side)
    if prevent_negative_effect(
        state,
        opponent_side,
        source="Nodowa",
        description=f"remove {target.card.name} from the Temporary Zone",
    ):
        return
    remove_temporary(state, opponent_side, target, disrupted=True)


def _read_the_move(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    target = _choose_opponent_temporary(state, side, card, context)
    if target is None:
        return

    opponent_side = state.opponent_side(side)
    if prevent_negative_effect(
        state,
        opponent_side,
        source="Read the Move",
        description=f"remove {target.card.name} from the Temporary Zone",
    ):
        return

    remove_temporary(state, opponent_side, target, disrupted=True)
    gain_momentum(state, side, 1)
    draw_one(state, side)


def _pull(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    use_cost = context.choice("pay_pull_cost")
    if use_cost is None:
        raise ChoiceRequired(card.name, "pay_pull_cost", [True, False])

    if use_cost:
        fighter = state.fighter(side)
        if not fighter.discard_pile:
            raise IllegalPlay("Pull cannot pay its optional cost with an empty discard pile.")

        if len(fighter.discard_pile) == 1:
            index = 0
        else:
            index = context.choice("discard_index")
            options = list(range(len(fighter.discard_pile)))
            if index not in options:
                raise ChoiceRequired(card.name, "discard_index", options)

        lose_momentum(state, side, 1)
        lose_position(state, side, 1)
        recovered = fighter.discard_pile.pop(index)
        fighter.draw_pile.insert(0, recovered)
        state.log(f"{fighter.wrestler.name} puts {recovered.name} on top of the Draw Pile.")

    add_temporary(state, side, card, phase="exchange")


def _power_water(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    fighter = state.fighter(side)
    if not fighter.discard_pile:
        return

    max_count = min(4, len(fighter.discard_pile))
    selected = context.choice("discard_indices")
    if selected is None:
        if max_count == 1:
            selected = [0]
        else:
            raise ChoiceRequired(
                card.name,
                "discard_indices",
                list(range(len(fighter.discard_pile))),
            )

    selected = list(selected)
    if not 1 <= len(selected) <= max_count:
        raise ValueError("Power Water must choose between 1 and 4 discard cards.")
    if len(set(selected)) != len(selected):
        raise ValueError("Power Water discard choices must be unique.")
    if any(i < 0 or i >= len(fighter.discard_pile) for i in selected):
        raise ValueError("Power Water discard choice is out of range.")

    if len(selected) == 1:
        hand_index = selected[0]
    else:
        hand_index = context.choice("hand_index")
        if hand_index not in selected:
            raise ChoiceRequired(card.name, "hand_index", selected)

    chosen_cards = [fighter.discard_pile[i] for i in selected]
    hand_card = fighter.discard_pile[hand_index]
    for i in sorted(selected, reverse=True):
        fighter.discard_pile.pop(i)

    fighter.hand.append(hand_card)
    for chosen in chosen_cards:
        if chosen is not hand_card:
            fighter.draw_pile.append(chosen)

    state.log(f"{fighter.wrestler.name} recovers {hand_card.name} with Power Water.")


GRIP_REFERENCING_TEMPORARIES: frozenset[str] = frozenset({
    "Attempt Two-Handed Grip",
    "Attempt Deep Outside Grip",
    "Attempt Deep Inside Grip",
    "Kannuki",
    "Morozashi",
})

GRIP_REFERENCING_KIMARITE: frozenset[str] = frozenset({
    "Yorikiri",
    "Yoritaoshi",
    "Katasukashi",
    "Tottari",
    "Uwatenage",
    "Hikiotoshi",
    "Tsuridashi",
    "Kotenage",
    "Abisetaoshi",
})


def _ottsuke(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    opponent_side = state.opponent_side(side)
    opponent = state.opponent(side)

    grips = []
    if opponent.left_grip is not GripState.NONE:
        grips.append("left")
    if opponent.right_grip is not GripState.NONE:
        grips.append("right")

    temp_targets = [
        instance
        for instance in opponent.temporary_zone
        if instance.card.name in GRIP_REFERENCING_TEMPORARIES
    ]
    kimarite_targets = [
        target
        for target in opponent.kimarite_zone
        if target.name in GRIP_REFERENCING_KIMARITE
    ]

    modes = []
    if grips:
        modes.append("reduce_grip")
    if temp_targets or kimarite_targets:
        modes.append("remove_card")
    if not modes:
        return

    mode = modes[0] if len(modes) == 1 else context.choice("mode")
    if mode not in modes:
        raise ChoiceRequired(card.name, "mode", modes)

    if mode == "reduce_grip":
        chosen = grips[0] if len(grips) == 1 else context.choice("grip")
        if chosen not in grips:
            raise ChoiceRequired(card.name, "grip", grips)
        if not prevent_negative_effect(
            state,
            opponent_side,
            source="Ottsuke",
            description=f"reduce {chosen.title()} Grip",
        ):
            reduce_grip(state, opponent_side, hand=chosen)
        return

    targets = [
        ("temporary", i, instance.card.name)
        for i, instance in enumerate(temp_targets)
    ] + [
        ("kimarite", i, target.name)
        for i, target in enumerate(kimarite_targets)
    ]
    if len(targets) == 1:
        target_type, target_index, target_name = targets[0]
    else:
        choice = context.choice("card_target")
        options = list(range(len(targets)))
        if choice not in options:
            raise ChoiceRequired(card.name, "card_target", options)
        target_type, target_index, target_name = targets[choice]

    if prevent_negative_effect(
        state,
        opponent_side,
        source="Ottsuke",
        description=f"remove {target_name}",
    ):
        return

    if target_type == "temporary":
        remove_temporary(
            state,
            opponent_side,
            temp_targets[target_index],
            disrupted=True,
        )
    else:
        target = kimarite_targets[target_index]
        opponent.kimarite_zone.remove(target)
        opponent.discard_pile.append(target)
        state.log(f"Ottsuke removes {target.name} from the opponent Kimarite Zone.")

    gain_momentum(state, side, 1)
    gain_push(state, side, 1)


def _morozashi(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    fighter = state.fighter(side)
    if fighter.left_grip is GripState.NONE and fighter.right_grip is GripState.NONE:
        raise IllegalPlay("Morozashi requires at least one Level 1 Grip.")
    if fighter.left_grip is GripState.DEEP or fighter.right_grip is GripState.DEEP:
        raise IllegalPlay("Morozashi requires an existing Level 1 Grip, not only Deep Grip.")

    if fighter.left_grip is GripState.NONE:
        establish_grip(state, side, "left")
    elif fighter.right_grip is GripState.NONE:
        establish_grip(state, side, "right")

    add_temporary(state, side, card, phase="exchange")


def _sidestep(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    if state.side_by_side_owner is not None:
        raise IllegalPlay("The bout is already Side-by-Side.")

    state.side_by_side_owner = side
    state.side_by_side_distance = abs(state.position)
    state.position = 0
    state.log(
        f"{state.fighter(side).wrestler.name} enters Side-by-Side at "
        f"distance {state.side_by_side_distance}."
    )
    add_temporary(state, side, card, phase="exchange")

EXCHANGE_EFFECTS: dict[str, ExchangeEffect] = {
    "Oshi": _oshi,
    "Tsuki": _tsuki,
    "Tsuppari": _tsuppari,
    "Harite": _harite,
    "Nodowa": _nodowa,
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
    "Power Water": _power_water,
    "Belt Slap": _belt_slap,
    "Ottsuke": _ottsuke,
    "Tsuri": _tsuri,
    "Yori": _yori,
    "Gaburi": _gaburi,
    "Hold Position": _hold_position,
    "Immovable": _immovable,
    "Henka": _henka,
    "Pull": _pull,
    "Sidestep": _sidestep,
    "Reset to Neutral": _reset_to_neutral,
    "Get Underneath": _get_underneath,
    "Read the Move": _read_the_move,
    "Regain Balance": _regain_balance,
    "Use the Tawara": _use_the_tawara,
    "Kannuki": _kannuki,
    "Morozashi": _morozashi,
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

UNIMPLEMENTED_TEMPORARY_CARD_NAMES: frozenset[str] = frozenset()

CHOICE_OR_TEMPORARY_EFFECTS_NOT_YET_REGISTERED: frozenset[str] = frozenset()


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
