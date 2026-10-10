from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .models import BoutState, Card, GripState, Side, Stat
from .prevention import prevent_negative_effect
from .rules import (
    effective_total_grip,
    establish_grip,
    gain_flexible_grip,
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


def lose_to_empty_draw(state: BoutState, side: Side) -> bool:
    fighter = state.fighter(side)
    if fighter.draw_pile:
        return False
    state.log(
        f"{fighter.wrestler.name} attempts to draw from an empty Draw Pile."
    )
    state.declare_winner(state.opponent_side(side), "Exhaustion")
    return True


def draw_one(state: BoutState, side: Side) -> Card | None:
    fighter = state.fighter(side)
    if lose_to_empty_draw(state, side):
        return None
    card = fighter.draw_pile.pop(0)
    fighter.hand.append(card)
    state.log(f"{fighter.wrestler.name} draws {card.name}.")
    return card


def draw_from_look(
    state: BoutState,
    side: Side,
    *,
    look: int,
    keep: int = 1,
    required_draws: int = 1,
) -> list[Card]:
    fighter = state.fighter(side)
    if len(fighter.draw_pile) < required_draws:
        state.log(
            f"{fighter.wrestler.name} cannot complete a required draw of "
            f"{required_draws} card(s) from the Draw Pile."
        )
        state.declare_winner(state.opponent_side(side), "Exhaustion")
        return []
    return ai_look_keep(fighter, look, keep)


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
    # Check momentum before resolving this card's effects.
    can_push = state.momentum * state.sign(side) >= 0
    if can_push:
        gain_push(state, side, 1)
    add_play(state, side)
    if state.winner is None:
        draw_one(state, side)


def _discard_from_hand(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    fighter = state.fighter(side)
    if not fighter.hand:
        return
    index = 0 if len(fighter.hand) == 1 else context.choice("hand_index")
    options = list(range(len(fighter.hand)))
    if index not in options:
        raise ChoiceRequired(card.name, "hand_index", options)
    discarded = fighter.hand.pop(index)
    fighter.discard_pile.append(discarded)
    state.log(f"{fighter.wrestler.name} discards {discarded.name} with {card.name}.")


def _shove(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    chained = any(played.name in {"Oshi", "Tsuki", "Tsuppari"}
                  for played in state.fighter(side).played_this_turn[:-1])
    gain_push(state, side, 1)
    if chained and state.winner is None:
        draw_one(state, side)
        if state.winner is None:
            _discard_from_hand(state, side, card, context)


def _explosive_step(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    before = state.momentum * state.sign(side)
    gain_momentum(state, side, 1)
    if before <= 0:
        gain_push(state, side, 1)


def _tsuki(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    can_disrupt = state.momentum * state.sign(side) >= 0
    add_play(state, side)
    if can_disrupt:
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
            state, state.opponent_side(side), source=card.name,
            description=f"reduce {chosen.title()} Grip",
        ):
            reduce_grip(state, state.opponent_side(side), hand=chosen)
    if state.winner is None:
        draw_one(state, side)


def _big_tsuki(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    can_disrupt = state.momentum * state.sign(side) >= 1
    if not can_disrupt:
        add_play(state, side)
        if state.winner is None:
            draw_one(state, side)
        return
    opponent = state.opponent(side)
    modes = []
    if opponent.left_grip is not GripState.NONE or opponent.right_grip is not GripState.NONE:
        modes.append("grip")
    if opponent.temporary_zone:
        modes.append("temporary")
    mode = (modes[0] if len(modes) == 1 else context.choice("mode")) if modes else None
    if len(modes) > 1 and mode not in modes:
        raise ChoiceRequired(card.name, "mode", modes)
    if mode == "grip":
        _tsuki(state, side, card, context)
        return
    add_play(state, side)
    if mode == "temporary":
        target = _choose_opponent_temporary(state, side, card, context)
        if target is not None and not prevent_negative_effect(
            state, state.opponent_side(side), source=card.name,
            description=f"remove {target.card.name} from Temporary Zone"):
            remove_temporary(state, state.opponent_side(side), target, disrupted=True)
    if state.winner is None:
        draw_one(state, side)


def _tsuppari(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    fighter = state.fighter(side)
    chained = any(
        played.name in {"Oshi", "Tsuki", "Tsuppari", "Shove"}
        for played in fighter.played_this_turn[:-1]
    )
    gain_momentum(state, side, 1)
    if chained and state.winner is None:
        gain_push(state, side, 1)
    if state.winner is None:
        add_play(state, side, 1)
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
    improve_grip(state, side, "left")
    add_temporary(state, side, card, phase="exchange")


def _gain_right_grip(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    fighter = state.fighter(side)
    improve_grip(state, side, "right")
    add_temporary(state, side, card, phase="exchange")


def _uwate(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    """Look based on total Grip; Deep Left Grip plays a selected card for free."""
    from .selection import ai_choose_from_look, keep_and_bottom, look_from_top
    from .legality import can_play_card
    from .playing import play_card

    fighter = state.fighter(side)
    improve_grip(state, side, "left")
    add_temporary(state, side, card, phase="exchange")
    if state.winner is not None:
        return

    looked = look_from_top(fighter, fighter.total_grip)
    if not looked:
        return

    deep = fighter.left_grip is GripState.DEEP
    if deep:
        # Temporarily allow one Play to make the selected follow-up free.
        fighter.plays_remaining += 1
        eligible = []
        for candidate in looked:
            fighter.hand.append(candidate)
            is_legal = can_play_card(state, side, candidate)
            fighter.hand.pop()
            if is_legal:
                eligible.append(candidate)
        if not eligible:
            fighter.plays_remaining -= 1
            keep_and_bottom(fighter, looked, [])
            return
    else:
        eligible = looked

    chosen_index = context.choice("uwate_card_index")
    if chosen_index is None:
        if context.choice("__human__") and len(eligible) > 1:
            raise ChoiceRequired(
                card.name, "uwate_card_index",
                [i for i, candidate in enumerate(looked) if candidate in eligible],
            )
        chosen = ai_choose_from_look(eligible, fighter.wrestler, 1)[0]
    else:
        if not isinstance(chosen_index, int) or not 0 <= chosen_index < len(looked):
            raise ChoiceRequired(card.name, "uwate_card_index", list(range(len(looked))))
        chosen = looked[chosen_index]
        if chosen not in eligible:
            raise IllegalPlay("Uwate's selected card cannot currently be played.")

    keep_and_bottom(fighter, looked, [chosen])
    if deep:
        play_card(state, side, chosen, context=context)



def _shitate(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    fighter = state.fighter(side)
    if fighter.right_grip is GripState.DEEP:
        gain_push(state, side, 2)
    else:
        improve_grip(state, side, "right")
    add_temporary(state, side, card, phase="exchange")


def _salt_throw(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    fighter = state.fighter(side)
    if len(fighter.discard_pile) >= 7:
        fighter.draw_pile.extend(fighter.discard_pile)
        fighter.discard_pile.clear()
        state.log(f"{fighter.wrestler.name} recycles the discard pile with Salt Throw.")
    add_temporary(state, side, card, phase="exchange")


def _stare_down(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    look = 1 + tachiai_comparisons_won(context, side)
    draw_from_look(state, side, look=look, keep=1)


def _belt_slap(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    gain_push(state, side, 1)
    if tachiai_advantage(context, side, Stat.SPIRIT) >= 3:
        gain_momentum(state, side, 1)


def _tsuri(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    if effective_total_grip(state, side, consume_prevention=True) < 1:
        gain_flexible_grip(state, side)
    else:
        gain_power(state, side, 1)
    if state.winner is None:
        add_temporary(state, side, card, phase="exchange")


def _yori(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    if effective_total_grip(state, side, consume_prevention=True) < 1:
        gain_flexible_grip(state, side)
    else:
        gain_push(state, side, 1)
    if state.winner is None:
        add_temporary(state, side, card, phase="exchange")


def _gaburi(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    if effective_total_grip(state, side, consume_prevention=True) < 1:
        gain_flexible_grip(state, side)
    else:
        gain_momentum(state, side, 1)
    if state.winner is None:
        add_temporary(state, side, card, phase="exchange")


def _henka(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    draw_one(state, side)


def _reset_to_neutral(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    for owner in (side, state.opponent_side(side)):
        for instance in list(state.fighter(owner).temporary_zone):
            remove_temporary(state, owner, instance, disrupted=True)
    state.side_by_side_owner = None
    state.side_by_side_distance = 0
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
    draw_one(state, side)
    if state.winner is None and state.momentum * state.sign(side) < 0:
        gain_momentum(state, side, 2)
        gain_power(state, side, 2)


def _give_ground(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    lose_position(state, side, 1)
    gain_momentum(state, side, 1)
    gain_power(state, side, 1)
    if state.winner is None:
        draw_one(state, side)



def _headlong_charge(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    fighter = state.fighter(side)
    if not fighter.kimarite_zone:
        return

    choice = context.choice("sacrifice_kimarite")
    options = [None] + list(range(len(fighter.kimarite_zone)))

    if choice not in options:
        raise ChoiceRequired(card.name, "sacrifice_kimarite", options)

    if choice is None:
        return

    sacrificed = fighter.kimarite_zone.pop(choice)
    fighter.discard_pile.append(sacrificed)
    state.log(f"{fighter.wrestler.name} sacrifices {sacrificed.name}.")

    gain_momentum(state, side, 1)
    gain_push(state, side, 1)


def _attempt_two_handed(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    fighter = state.fighter(side)
    chosen = context.choice("grip")
    if chosen not in {"left", "right"}:
        chosen = "left" if fighter.left_grip <= fighter.right_grip else "right"
    establish_grip(state, side, chosen)
    add_temporary(state, side, card, phase="exchange")


def _attempt_deep_outside(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    establish_grip(state, side, "left")
    add_temporary(state, side, card, phase="exchange")


def _attempt_deep_inside(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    establish_grip(state, side, "right")
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


def _search_kimarite(state: BoutState, searched_side: Side, source: str,
                     context: EffectContext | None = None) -> None:
    """Select a Kimarite from a Draw Pile; prompt when several exist.

    AI callers without a context retain deterministic first-eligible selection.
    """
    fighter = state.fighter(searched_side)
    options = [i for i, card in enumerate(fighter.draw_pile) if card.is_kimarite]
    if not options:
        return
    choice = None if context is None else context.choice("kimarite_index")
    if len(options) == 1:
        selected = options[0]
    elif context is None or not context.choice("__human__"):
        # Noninteractive AI selects deterministically, unless its controller
        # explicitly nominates a valid eligible card.
        selected = choice if choice in options else options[0]
    else:
        if choice not in options:
            raise ChoiceRequired(source, "kimarite_index", options)
        selected = choice
    found = fighter.draw_pile.pop(selected)
    fighter.kimarite_zone.append(found)
    state.log(f"{fighter.wrestler.name} searches {found.name} into the Kimarite Zone after {source}.")


def give_opponent_kimarite(state: BoutState, side: Side, source: str,
                           context: EffectContext | None = None) -> None:
    _search_kimarite(state, state.opponent_side(side), source, context)


def _get_underneath(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    gain_momentum(state, side, 1)
    gain_push(state, side, 1)
    if state.winner is None:
        # The opponent owns this search choice. Do not expose their hidden
        # Draw Pile or let the acting human pick on their behalf.
        give_opponent_kimarite(state, side, card.name)


def _use_the_tawara(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    lose_position(state, side, 1)
    if state.winner is None:
        gain_momentum(state, side, 1)
    _search_kimarite(state, side, card.name, context)
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
    if context.choice("__human__") and state.opponent(side).temporary_zone and context.choice("mode") not in {"draw", "remove"}:
        raise ChoiceRequired(card.name, "mode", ["remove", "draw"])
    if context.choice("mode") == "draw" or not state.opponent(side).temporary_zone:
        draw_one(state, side)
        return
    target = _choose_opponent_temporary(state, side, card, context)
    if target is None:
        draw_one(state, side)
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
    """Current Pull choice: setup a reversal or filter one card."""
    if context.choice("__human__") and context.choice("mode") not in {"reversal", "filter"}:
        raise ChoiceRequired(card.name, "mode", ["reversal", "filter"])
    if context.choice("mode") in {"filter", "draw_discard"}:
        draw_one(state, side)
        if state.winner is None:
            _discard_from_hand(state, side, card, context)
        # Pull is ordinarily a Temporary, but filter mode never enters it.
        state.fighter(side).discard_pile.append(card)
        return

    fighter = state.fighter(side)
    lose_momentum(state, side, 1)
    if state.winner is None:
        lose_position(state, side, 1)
    if fighter.discard_pile and state.winner is None:
        index = context.choice("discard_index")
        if not isinstance(index, int) or not 0 <= index < len(fighter.discard_pile):
            index = len(fighter.discard_pile) - 1
        recovered = fighter.discard_pile.pop(index)
        fighter.draw_pile.insert(0, recovered)
        state.log(f"{fighter.wrestler.name} puts {recovered.name} on top of the Draw Pile.")
    if state.winner is None:
        add_temporary(state, side, card, phase="exchange")


def _power_water(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    import hashlib
    import random

    fighter = state.fighter(side)
    cantrips = [
        Card(62, "Power Water Cantrip")
        for _ in range(6)
    ]

    # Derive a reproducible shuffle from the current bout state.
    signature = repr((
        state.turn_number,
        side.value,
        tuple((c.card_id, c.name) for c in fighter.draw_pile),
        tuple((c.card_id, c.name) for c in fighter.discard_pile),
        tuple((s.value, card_id) for s, card_id in state.card_play_ids),
    ))
    seed = int.from_bytes(
        hashlib.sha256(signature.encode("utf-8")).digest()[:8],
        "big",
    )

    fighter.draw_pile.extend(cantrips)
    random.Random(seed).shuffle(fighter.draw_pile)
    state.log(f"{fighter.wrestler.name} shuffles 6 Power Water Cantrips into the Draw Pile.")


def _power_water_cantrip(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    fighter = state.fighter(side)
    if fighter.discard_pile:
        index = context.choice("discard_index")
        if index is None:
            index = len(fighter.discard_pile) - 1
        if not isinstance(index, int) or not 0 <= index < len(fighter.discard_pile):
            raise ValueError("Invalid Power Water Cantrip discard index.")
        recovered = fighter.discard_pile.pop(index)
        fighter.hand.append(recovered)
        state.log(f"{fighter.wrestler.name} recovers {recovered.name}.")
    add_play(state, side, 1)
    draw_one(state, side)


GRIP_REFERENCING_TEMPORARIES = frozenset({
    "Gain Left Grip",
    "Gain Right Grip",
    "Uwate",
    "Shitate",
    "Attempt Two-Handed Grip",
    "Attempt Deep Outside Grip",
    "Attempt Deep Inside Grip",
    "Morozashi",
    "Kannuki",
})

GRIP_REFERENCING_KIMARITE = frozenset({
    "Yorikiri",
    "Yoritaoshi",
    "Uwatenage",
    "Shitatenage",
    "Hikiotoshi",
    "Tsuridashi",
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
        state.kimarite_removals.append((side, target.name))
        state.log(f"Ottsuke removes {target.name} from the opponent Kimarite Zone.")

    gain_momentum(state, side, 1)


def _morozashi(
    state: BoutState, side: Side, card: Card, context: EffectContext
) -> None:
    fighter = state.fighter(side)
    if fighter.left_grip is GripState.NONE and fighter.right_grip is GripState.NONE:
        raise IllegalPlay("Morozashi requires at least one Grip.")

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
    "Injury": lambda state, side, card, context: None,
    "Oshi": _oshi,
    "Shove": _shove,
    "Explosive Step — Fumikomi": _explosive_step,
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
    "Power Water Cantrip": _power_water_cantrip,
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


# BEGIN APPROVED MILL/RECYCLE V1
MILL_AMOUNTS = {
    "Headlong Charge": 2,
    "Explosive Step — Fumikomi": 2,
    "Tsuppari": 1,
    "Oshi": 1,
    "Tsuki": 1,
    "Shove": 1,
}
RECYCLE_NAMES = frozenset({
    "Gain Left Grip", "Gain Right Grip", "Uwate", "Shitate",
    "Morozashi", "Use the Tawara",
})


def mill_cards(state: BoutState, side: Side, amount: int) -> None:
    """Move up to X cards from top of Draw Pile to Discard Pile; never draw."""
    fighter = state.fighter(side)
    moved = min(amount, len(fighter.draw_pile))
    for _ in range(moved):
        fighter.discard_pile.append(fighter.draw_pile.pop(0))
    state.log(f"{fighter.wrestler.name} mills {moved} card(s).")


def recycle_one(state: BoutState, side: Side, context: EffectContext) -> None:
    """Return one discarded card to bottom of Draw Pile.

    An explicit discard_index selects a card when present. The AI/default
    deterministically selects the last discarded card to avoid choice deadlocks.
    """
    fighter = state.fighter(side)
    if not fighter.discard_pile:
        return
    selected = context.choice("recycle_discard_index")
    if selected is None:
        selected = len(fighter.discard_pile) - 1
    if not isinstance(selected, int) or not 0 <= selected < len(fighter.discard_pile):
        raise ValueError("Invalid recycling discard index.")
    recovered = fighter.discard_pile.pop(selected)
    fighter.draw_pile.append(recovered)
    state.log(f"{fighter.wrestler.name} recycles {recovered.name} to the bottom of the Draw Pile.")


def _with_resource_cost(name: str, original: ExchangeEffect) -> ExchangeEffect:
    def effect(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
        original(state, side, card, context)
        if state.winner is not None:
            return
        if name in MILL_AMOUNTS:
            mill_cards(state, side, MILL_AMOUNTS[name])
        if name in RECYCLE_NAMES:
            recycle_one(state, side, context)
    return effect


for _name in (*MILL_AMOUNTS, *RECYCLE_NAMES):
    if _name not in EXCHANGE_EFFECTS:
        raise RuntimeError(f"Missing exchange effect for {_name}")
    EXCHANGE_EFFECTS[_name] = _with_resource_cost(_name, EXCHANGE_EFFECTS[_name])
# END APPROVED MILL/RECYCLE V1


TEMPORARY_CARD_NAMES: frozenset[str] = frozenset(
    {
        "Salt Throw",
        "Tsuri",
        "Yori",
        "Gaburi",
        "Gain Left Grip",
        "Gain Right Grip",
        "Uwate",
        "Shitate",
        "Attempt Two-Handed Grip",
        "Attempt Deep Outside Grip",
        "Attempt Deep Inside Grip",
        "Hold Position",
        "Immovable",
        "Pull",
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
