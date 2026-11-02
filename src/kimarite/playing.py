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
from .rules import discard_normally, gain_momentum, lose_momentum


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

    # B9: each subsequent card played after Morotezuki generates one Push.
    primed = any(c.name == "Morotezuki" for c in fighter.played_this_turn)
    fighter.hand.remove(card)
    fighter.plays_remaining -= 1
    fighter.cards_played_this_turn += 1
    fighter.played_this_turn.append(card)
    state.card_plays.append((side, card.name))
    state.card_play_ids.append((side, card.card_id))
    state.log(f"{fighter.wrestler.name} plays {card.name}.")

    # Playing later cards fuels Hakkeyoi! immediately; its opponent reaction
    # occurs once on the opponent's third card before the next owner's turn.
    previous_hakkeyoi = sum(
        played.name == "Hakkeyoi!" for played in fighter.played_this_turn[:-1]
    )
    for _ in range(previous_hakkeyoi):
        if state.winner is None:
            gain_momentum(state, side, 1)
    if fighter.cards_played_this_turn == 3:
        opponent_side = state.opponent_side(side)
        for instance in tuple(state.fighter(opponent_side).temporary_zone):
            if instance.card.name == "Hakkeyoi!" and state.winner is None:
                lose_momentum(state, opponent_side, 1)

    if state.winner is not None:
        return
    if primed:
        from .rules import gain_push
        gain_push(state, side, 1)
        if state.winner is not None:
            return

    if card.is_kimarite:
        fighter.kimarite_zone.append(card)
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
        discard_normally(state, side, card)
