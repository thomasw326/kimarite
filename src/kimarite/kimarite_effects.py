from __future__ import annotations

from .effects import ChoiceRequired, EffectContext, add_play, draw_from_look, draw_one
from .kimarite import no_grip, power_advantage, relative_momentum, relative_position
from .models import BoutState, Card, GripState, Side
from .prevention import prevent_negative_effect
from .rules import effective_total_grip, establish_grip, gain_flexible_grip, gain_momentum, gain_position, lose_position, gain_power, lose_momentum, reduce_grip, establish_grip
from .selection import ai_look_keep


def _optional(context: EffectContext, key: str, card: Card) -> bool:
    value = context.choice(key)
    if value is None:
        raise ChoiceRequired(card.name, key, [True, False])
    return bool(value)


def _bottom_one_from_hand(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    fighter = state.fighter(side)
    if not fighter.hand:
        return
    if len(fighter.hand) == 1:
        index = 0
    else:
        index = context.choice("hand_index")
        if index is None and not context.choice("__human__"):
            from .ai import _best_hand_index
            index = _best_hand_index(state, side, prefer_discard=True)
        options = list(range(len(fighter.hand)))
        if index not in options:
            raise ChoiceRequired(card.name, "hand_index", options)
    bottomed = fighter.hand.pop(index)
    fighter.draw_pile.append(bottomed)
    state.log(f"{fighter.wrestler.name} bottoms {bottomed.name}.")


def _discard_one_from_hand(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    fighter = state.fighter(side)
    if not fighter.hand:
        return
    options = list(range(len(fighter.hand)))
    index = 0 if len(options) == 1 else context.choice("hand_index")
    if index is None and not context.choice("__human__"):
        from .ai import _best_hand_index
        index = _best_hand_index(state, side, prefer_discard=True)
    if index not in options:
        raise ChoiceRequired(card.name, "hand_index", options)
    discarded = fighter.hand.pop(index)
    fighter.discard_pile.append(discarded)
    state.log(f"{fighter.wrestler.name} discards {discarded.name} with {card.name}.")


def resolve_kimarite_play_effect(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    if state.disable_kimarite_exchange_effects:
        return
    fighter = state.fighter(side)
    opponent_side = state.opponent_side(side)

    if card.name == "Yorikiri":
        if effective_total_grip(state, side) >= 2:
            from .rules import gain_push
            gain_push(state, side, 1)

    elif card.name == "Oshidashi":
        if relative_position(state, side) >= 1:
            gain_momentum(state, side, 1)

    elif card.name == "Tsukidashi":
        if relative_position(state, side) >= 1:
            add_play(state, side, 1)
            if state.winner is None:
                draw_one(state, side)

    elif card.name == "Oshitaoshi":
        if relative_momentum(state, side) >= 1:
            gain_power(state, side, 1)
        if power_advantage(state, side) >= 1:
            gain_momentum(state, side, 1)

    elif card.name == "Yoritaoshi":
        if effective_total_grip(state, side) >= 1:
            gain_power(state, side, 1)

    elif card.name == "Katasukashi":
        if relative_momentum(state, side) >= 1 and fighter.discard_pile:
            options = list(range(len(fighter.discard_pile)))
            index = options[0] if len(options) == 1 else context.choice("discard_index")
            if index not in options:
                raise ChoiceRequired(card.name, "discard_index", options)
            fighter.hand.append(fighter.discard_pile.pop(index))

    elif card.name == "Tsukiotoshi":
        add_play(state, side, 1)

    elif card.name == "Tottari":
        opponent = state.opponent(side)
        looked = list(opponent.draw_pile[:3])
        if not looked:
            return
        if len(looked) == 1:
            index = 0
        else:
            index = context.choice("opponent_deck_index")
            options = list(range(len(looked)))
            if index not in options:
                raise ChoiceRequired(card.name, "opponent_deck_index", options)
        target = looked[index]
        opponent.draw_pile.remove(target)
        opponent.discard_pile.append(target)
        state.log(f"{fighter.wrestler.name} discards {target.name} from the opponent deck.")

    elif card.name == "Uwatenage":
        if relative_momentum(state, side) >= 0:
            establish_grip(state, side, "left")

    elif card.name == "Shitatenage":
        if fighter.right_grip is not GripState.NONE:
            gain_momentum(state, side, 1)

    elif card.name == "Hatakikomi":
        if _optional(context, "use_optional", card):
            lose_momentum(state, side, 1)
            opponent = state.opponent(side)
            if opponent.hand:
                if len(opponent.hand) == 1:
                    index = 0
                else:
                    index = context.choice("opponent_hand_index")
                    options = list(range(len(opponent.hand)))
                    if index not in options:
                        raise ChoiceRequired(card.name, "opponent_hand_index", options)
                discarded = opponent.hand.pop(index)
                opponent.discard_pile.append(discarded)
            else:
                draw_one(state, side)

    elif card.name == "Hikiotoshi":
        draw_from_look(state, side, look=3, keep=1)

    elif card.name == "Tsukitaoshi":
        add_play(state, side, 1)
        draw_one(state, side)
        _discard_one_from_hand(state, side, card, context)

    elif card.name == "Tsuridashi":
        gain_power(state, side, 1)
        if relative_momentum(state, side) >= 2:
            gain_power(state, side, 1)

    elif card.name == "Kotenage":
        opponent = state.opponent(side)
        available = []
        if opponent.left_grip is not GripState.NONE:
            available.append("left")
        if opponent.right_grip is not GripState.NONE:
            available.append("right")
        if available:
            chosen = available[0] if len(available) == 1 else context.choice("grip")
            if chosen not in available:
                raise ChoiceRequired(card.name, "grip", available)
            if not prevent_negative_effect(
                state, opponent_side, source="Kotenage",
                description=f"reduce {chosen.title()} Grip",
            ):
                reduce_grip(state, opponent_side, hand=chosen)
        elif _optional(context, "cycle_if_no_grip", card):
            draw_one(state, side)
            if fighter.hand:
                index = 0 if len(fighter.hand) == 1 else context.choice("hand_index")
                if index is None and not context.choice("__human__"):
                    from .ai import _best_hand_index
                    index = _best_hand_index(state, side, prefer_discard=True)
                options = list(range(len(fighter.hand)))
                if index not in options:
                    raise ChoiceRequired(card.name, "hand_index", options)
                discarded = fighter.hand.pop(index)
                fighter.discard_pile.append(discarded)

    elif card.name == "Kirikaeshi":
        # B9: optional conversion of Power into Momentum and a card.
        if context.choice("use_optional") is True:
            from .rules import lose_power
            lose_power(state, side, 1)
            gain_momentum(state, side, 1)
            if state.winner is None:
                draw_one(state, side)

    elif card.name in {"Okuridashi", "Okuritaoshi"}:
        return  # B9 generated-only: no Exchange effect.

    elif card.name == "Tsuriotoshi":
        mode = context.choice("mode") or "power"
        if mode == "power":
            gain_power(state, side, 1)
        elif mode == "momentum":
            gain_momentum(state, side, 1)
        elif mode == "grip":
            gain_flexible_grip(state, side)
        else:
            raise ChoiceRequired(card.name, "mode", ["power", "momentum", "grip"])

    elif card.name == "Sukuinage":
        if no_grip(state, side):
            draw_one(state, side)

    elif card.name == "Utchari":
        if relative_position(state, side) < 0:
            draw_from_look(state, side, look=2, keep=1)

    elif card.name == "Uwatedashinage":
        draw_one(state, side)
        if fighter.hand:
            value = context.choice("discard_for_grip")
            if value is None:
                raise ChoiceRequired(card.name, "discard_for_grip", [True, False])
            if value:
                _discard_one_from_hand(state, side, card, context)
                establish_grip(state, side, "left")

    elif card.name == "Abisetaoshi":
        if fighter.power >= 6:
            if effective_total_grip(state, side) == 0:
                gain_flexible_grip(state, side)
            else:
                gain_power(state, side, 1)

    else:
        raise KeyError(f"No Kimarite play effect registered for {card.name!r}.")
