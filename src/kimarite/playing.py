from __future__ import annotations

from .effects import (
    EffectContext,
    IllegalPlay,
    TEMPORARY_CARD_NAMES,
    resolve_exchange_effect,
)
from .kimarite_effects import resolve_kimarite_play_effect
from .legality import can_play_card
from .models import BoutState, Card, Side


def play_card(
    state: BoutState,
    side: Side,
    card: Card,
    *,
    context: EffectContext | None = None,
) -> None:
    fighter = state.fighter(side)
    if state.winner is not None:
        raise IllegalPlay("The bout is already over.")
    if card not in fighter.hand:
        raise IllegalPlay(f"{card.name} is not in {fighter.wrestler.name}'s hand.")
    if fighter.plays_remaining <= 0:
        raise IllegalPlay(f"{fighter.wrestler.name} has no Plays remaining.")
    if not can_play_card(state, side, card):
        raise IllegalPlay(f"{card.name} is not currently a legal play.")

    fighter.hand.remove(card)
    fighter.plays_remaining -= 1
    fighter.cards_played_this_turn += 1
    fighter.played_this_turn.append(card)
    state.card_plays.append((side, card.name))
    state.card_play_ids.append((side, card.card_id))
    state.log(f"{fighter.wrestler.name} plays {card.name}.")
    previous_morotsuki = sum(
        previous.name == "Morotsuki" for previous in fighter.played_this_turn[:-1]
    )
    if previous_morotsuki:
        from .rules import gain_push
        gain_push(state, side, previous_morotsuki)
        if state.winner is not None:
            return

    if card.is_kimarite:
        duplicate_in_zone = any(
            previous.name == card.name for previous in fighter.kimarite_zone
        )
        fighter.kimarite_zone.append(card)
        if duplicate_in_zone and state.winner is None:
            fighter.plays_remaining += 1
            state.log(f"{fighter.wrestler.name} gains 1 Play for repeated {card.name}.")
        if getattr(state, "r20_active", False) and card.name.startswith("R21:"):
            from .r21_variant_rules import variant_exchange
            variant_exchange(state, side, card, context or EffectContext())
        elif getattr(state, "r20_active", False) and card.name.startswith("R20:"):
            from .r20_variant_rules import variant_exchange
            variant_exchange(state, side, card, context or EffectContext())
        else:
            resolve_kimarite_play_effect(
                state,
                side,
                card,
                context or EffectContext(),
            )
        return

    resolve_exchange_effect(
        state,
        side,
        card,
        context or EffectContext(),
    )
    if card.name == "Power Water Cantrip":
        state.log("Power Water Cantrip is exhausted and removed from the bout.")
    elif card.name not in TEMPORARY_CARD_NAMES and not (
        getattr(state, "r20_active", False) and card.name == "Henka"
    ):
        fighter.discard_pile.append(card)
