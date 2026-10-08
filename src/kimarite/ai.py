from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from .effects import ChoiceRequired, EffectContext, IllegalPlay
from .kimarite import satisfied_kimarite
from .models import BoutState, Card, GripState, Side
from .playing import play_card
from .rules import effective_total_grip
from .tachiai import TachiaiComparison


UNSUPPORTED_AI_CARDS = frozenset({"Sidestep"})


@dataclass(frozen=True)
class AIPlay:
    card: Card
    context: EffectContext
    score: float


def relative_momentum(state: BoutState, side: Side) -> int:
    return state.momentum * state.sign(side)


def relative_position(state: BoutState, side: Side) -> int:
    return state.position * state.sign(side)


def _card_priority(card: Card, state: BoutState, side: Side) -> tuple[int, int, int]:
    wrestler = state.fighter(side).wrestler
    return (
        card.orbs(wrestler.primary),
        card.orbs(wrestler.secondary),
        -card.card_id,
    )


def _best_grip_to_reduce(state: BoutState, side: Side) -> str:
    opponent = state.opponent(side)
    if int(opponent.left_grip) > int(opponent.right_grip):
        return "left"
    if int(opponent.right_grip) > int(opponent.left_grip):
        return "right"
    return "left"


def _best_hand_index(state: BoutState, side: Side, *, prefer_discard: bool) -> int:
    hand = state.fighter(side).hand
    if not hand:
        return 0
    ranked = sorted(
        range(len(hand)),
        key=lambda i: _card_priority(hand[i], state, side),
        reverse=not prefer_discard,
    )
    return ranked[0]


def _best_discard_index(state: BoutState, side: Side) -> int:
    discard = state.fighter(side).discard_pile
    ranked = sorted(
        range(len(discard)),
        key=lambda i: _card_priority(discard[i], state, side),
        reverse=True,
    )
    return ranked[0]


def _context_for_card(
    state: BoutState,
    side: Side,
    card: Card,
    comparison: TachiaiComparison,
) -> EffectContext:
    choices: dict[str, object] = {}

    opponent = state.opponent(side)
    fighter = state.fighter(side)

    if card.name in {"Tsuki", "Kotenage"}:
        if opponent.left_grip is not GripState.NONE and opponent.right_grip is not GripState.NONE:
            choices["grip"] = _best_grip_to_reduce(state, side)

    if card.name == "Use the Tawara":
        # Pay the optional Position cost only when Power is strategically useful
        # and doing so does not move the wrestler to the brink unnecessarily.
        choices["lose_position_for_power"] = (
            relative_position(state, side) > -2
            and fighter.power <= opponent.power
        )

    if card.name == "Pull":
        choices["pay_pull_cost"] = bool(fighter.discard_pile) and relative_momentum(state, side) <= -1
        if fighter.discard_pile:
            choices["discard_index"] = _best_discard_index(state, side)

    if card.name == "Power Water" and fighter.discard_pile:
        ranked = sorted(
            range(len(fighter.discard_pile)),
            key=lambda i: _card_priority(fighter.discard_pile[i], state, side),
            reverse=True,
        )
        selected = ranked[: min(4, len(ranked))]
        choices["discard_indices"] = selected
        choices["hand_index"] = selected[0]

    if card.name in {"Nodowa", "Read the Move"} and opponent.temporary_zone:
        priority = {
            "Headlong Charge": 100,
            "Morozashi": 90,
            "Kannuki": 85,
            "Attempt Two-Handed Grip": 80,
            "Attempt Deep Outside Grip": 75,
            "Attempt Deep Inside Grip": 75,
            "Hold Position": 70,
            "Immovable": 65,
            "Get Underneath": 60,
            "Use the Tawara": 55,
            "Pull": 50,
            "Shiko Stomp": 95,
        }
        best = max(
            range(len(opponent.temporary_zone)),
            key=lambda i: priority.get(opponent.temporary_zone[i].card.name, 0),
        )
        choices["temporary_index"] = best

    if card.name == "Ottsuke":
        removable_temps = [
            i for i, instance in enumerate(opponent.temporary_zone)
            if instance.card.name in {
                "Attempt Two-Handed Grip",
                "Attempt Deep Outside Grip",
                "Attempt Deep Inside Grip",
                "Kannuki",
                "Morozashi",
            }
        ]
        removable_kimarite = [
            i for i, target in enumerate(opponent.kimarite_zone)
            if target.name in {
                "Yorikiri", "Yoritaoshi", "Katasukashi", "Tottari",
                "Uwatenage", "Hikiotoshi", "Tsuridashi", "Kotenage",
                "Abisetaoshi",
            }
        ]
        if removable_temps or removable_kimarite:
            choices["mode"] = "remove_card"
            choices["card_target"] = 0
        elif opponent.left_grip is not GripState.NONE or opponent.right_grip is not GripState.NONE:
            choices["mode"] = "reduce_grip"
            if opponent.left_grip is not GripState.NONE and opponent.right_grip is not GripState.NONE:
                choices["grip"] = _best_grip_to_reduce(state, side)

    if card.name in {"Katasukashi", "Hikiotoshi", "Hatakikomi", "Tsukiotoshi"}:
        # AI accepts optional tactical conversion when the cost will not create
        # an immediate severe Momentum deficit.
        choices["use_optional"] = relative_momentum(state, side) >= -1

    if card.name == "Kotenage":
        choices["cycle_if_no_grip"] = True
        if fighter.hand:
            choices["hand_index"] = _best_hand_index(state, side, prefer_discard=True)

    if card.name == "Tsukitaoshi" and fighter.hand:
        choices["hand_index"] = _best_hand_index(state, side, prefer_discard=True)

    if card.name == "Tottari":
        looked = opponent.draw_pile[:3]
        if len(looked) > 1:
            choices["opponent_deck_index"] = max(
                range(len(looked)),
                key=lambda i: _card_priority(looked[i], state, state.opponent_side(side)),
            )

    if card.name == "Hatakikomi" and len(opponent.hand) > 1:
        choices["opponent_hand_index"] = max(
            range(len(opponent.hand)),
            key=lambda i: _card_priority(opponent.hand[i], state, state.opponent_side(side)),
        )

    return EffectContext(comparison=comparison, choices=choices)


def score_state(state: BoutState, side: Side) -> float:
    if state.winner is side:
        return 1_000_000.0
    if state.winner is state.opponent_side(side):
        return -1_000_000.0

    fighter = state.fighter(side)
    opponent = state.opponent(side)

    score = 0.0
    score += relative_momentum(state, side) * 18
    score += relative_position(state, side) * 20
    score += (fighter.power - opponent.power) * 5
    score += effective_total_grip(state, side) * 7
    score -= effective_total_grip(state, state.opponent_side(side)) * 5
    score += len(fighter.hand) * 1.5
    score -= len(opponent.hand) * 0.5
    score += fighter.plays_remaining * 0.5

    # A satisfied Kimarite at the current check is effectively decisive.
    try:
        if satisfied_kimarite(state, side):
            score += 100_000
    except KeyError:
        pass

    # Reward progress toward common win axes even before a full condition.
    score += max(0, relative_momentum(state, side)) * 3
    score += max(0, relative_position(state, side)) * 3
    if fighter.total_grip >= 2:
        score += 8
    if fighter.power >= 7:
        score += 6
    if fighter.cards_played_this_turn >= 4:
        score += 10

    return score


def candidate_plays(
    state: BoutState,
    side: Side,
    comparison: TachiaiComparison,
) -> list[AIPlay]:
    plays: list[AIPlay] = []
    for card in list(state.fighter(side).hand):
        if card.name in UNSUPPORTED_AI_CARDS:
            continue

        trial = deepcopy(state)
        trial_card = next(c for c in trial.fighter(side).hand if c.card_id == card.card_id)
        context = _context_for_card(trial, side, trial_card, comparison)
        try:
            play_card(trial, side, trial_card, context=context)
        except (IllegalPlay, ChoiceRequired, NotImplementedError, KeyError, ValueError):
            continue

        plays.append(AIPlay(card=card, context=context, score=score_state(trial, side)))

    return plays


def choose_play(
    state: BoutState,
    side: Side,
    comparison: TachiaiComparison,
) -> AIPlay | None:
    plays = candidate_plays(state, side, comparison)
    if not plays:
        return None

    current_score = score_state(state, side)
    best = max(
        plays,
        key=lambda play: (
            play.score,
            _card_priority(play.card, state, side),
        ),
    )

    # Prefer using available Plays in this prototype AI unless the move is
    # materially harmful. This still permits passing on clearly bad cards.
    if best.score < current_score - 8:
        return None
    return best


def play_ai_turn(
    state: BoutState,
    side: Side,
    comparison: TachiaiComparison,
    *,
    max_cards: int = 20,
) -> list[str]:
    played: list[str] = []
    for _ in range(max_cards):
        if state.winner is not None or state.fighter(side).plays_remaining <= 0:
            break

        choice = choose_play(state, side, comparison)
        if choice is None:
            break

        # Rebuild context against the live state; indices can shift after prior plays.
        live_context = _context_for_card(state, side, choice.card, comparison)
        try:
            play_card(state, side, choice.card, context=live_context)
        except (IllegalPlay, ChoiceRequired, NotImplementedError, KeyError, ValueError):
            break
        played.append(choice.card.name)

    return played
