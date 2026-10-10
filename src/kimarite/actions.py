"""Safe single-card actions and public/owner-facing Exchange observations.

This is a synchronous choice-level foundation, not a full turn scheduler.
For incomplete card choices the engine applies the play to a clone and leaves
the authoritative state untouched until the action fully resolves.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from .effects import ChoiceRequired, EffectContext, IllegalPlay
from .legality import can_play_card
from .models import BoutState, Side
from .playing import play_card
from .tachiai import TachiaiComparison


@dataclass(frozen=True)
class CardView:
    card_id: int
    name: str
    power: int
    technique: int
    spirit: int
    is_kimarite: bool


@dataclass(frozen=True)
class LegalAction:
    hand_index: int
    card: CardView


@dataclass(frozen=True)
class PlayerObservation:
    side: Side
    active_side: Side | None
    turn_number: int
    momentum: int
    position: int
    own_power: int
    opponent_power: int
    own_grip: tuple[int, int]
    opponent_grip: tuple[int, int]
    hand: tuple[CardView, ...]
    opponent_hand_size: int
    own_draw_count: int
    opponent_draw_count: int
    own_discard_count: int
    opponent_discard_count: int
    plays_remaining: int
    winner: Side | None


def _view(card) -> CardView:
    return CardView(card.card_id, card.name, card.power, card.technique,
                    card.spirit, card.is_kimarite)


def observe(state: BoutState, side: Side) -> PlayerObservation:
    """Return immutable public and own-card information only.

    In particular, no opponent hand names or draw-pile order are exposed.
    """
    own, other = state.fighter(side), state.opponent(side)
    return PlayerObservation(
        side=side, active_side=state.active_side, turn_number=state.turn_number,
        momentum=state.momentum * state.sign(side),
        position=state.position * state.sign(side),
        own_power=own.power, opponent_power=other.power,
        own_grip=(int(own.left_grip), int(own.right_grip)),
        opponent_grip=(int(other.left_grip), int(other.right_grip)),
        hand=tuple(map(_view, own.hand)),
        opponent_hand_size=len(other.hand),
        own_draw_count=len(own.draw_pile),
        opponent_draw_count=len(other.draw_pile),
        own_discard_count=len(own.discard_pile),
        opponent_discard_count=len(other.discard_pile),
        plays_remaining=own.plays_remaining,
        winner=state.winner,
    )


def legal_actions(state: BoutState, side: Side) -> tuple[LegalAction, ...]:
    if state.active_side is not side or state.winner is not None:
        return ()
    return tuple(
        LegalAction(i, _view(card))
        for i, card in enumerate(state.fighter(side).hand)
        if can_play_card(state, side, card)
    )


def submit_card_action(
    state: BoutState,
    side: Side,
    hand_index: int,
    *,
    choices: Mapping[str, Any] | None = None,
    comparison: TachiaiComparison | None = None,
) -> None:
    """Atomically submit one card action, including its effect choices.

    Raises ChoiceRequired for missing choices and IllegalPlay for invalid
    requests, leaving the original state completely unchanged in either case.
    """
    if state.active_side is not side or state.winner is not None:
        raise IllegalPlay("It is not this wrestler's active turn.")
    fighter = state.fighter(side)
    if not isinstance(hand_index, int) or not 0 <= hand_index < len(fighter.hand):
        raise IllegalPlay("Card index is not in the hand.")
    if not can_play_card(state, side, fighter.hand[hand_index]):
        raise IllegalPlay("This card cannot currently be played.")

    trial = deepcopy(state)
    trial_card = trial.fighter(side).hand[hand_index]
    play_card(trial, side, trial_card, context=EffectContext(comparison=comparison, choices=dict(choices or {})))
    # Preserve the BoutState object identity so callers can retain their handle.
    # All nested state belongs to the accepted transaction from this point on.
    state.__dict__.update(trial.__dict__)
