from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from .effects import ChoiceRequired, EffectContext, IllegalPlay
from .kimarite import satisfied_kimarite
from .models import BoutState, Card, GripState, Side
from .playing import play_card
from .rules import effective_total_grip
from .tachiai import TachiaiComparison


UNSUPPORTED_AI_CARDS = frozenset()


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

    if card.name == "Oshi":
        # Oshi itself leaves hand before its discard is resolved.
        remainder = [c for c in fighter.hand if c is not card]
        if remainder:
            choices["hand_index"] = min(range(len(remainder)), key=lambda i: _card_priority(remainder[i], state, side))

    if card.name in {"Tsuki", "Kotenage"}:
        if opponent.left_grip is not GripState.NONE and opponent.right_grip is not GripState.NONE:
            choices["grip"] = _best_grip_to_reduce(state, side)

    if card.name == "Power Water" and fighter.discard_pile:
        ranked = sorted(
            range(len(fighter.discard_pile)),
            key=lambda i: _card_priority(fighter.discard_pile[i], state, side),
            reverse=True,
        )
        selected = ranked[: min(4, len(ranked))]
        choices["discard_indices"] = selected
        choices["hand_index"] = selected[0]

    if card.name == "Read the Move":
        choices["mode"] = "remove" if opponent.temporary_zone else "draw"

    if card.name in {"Kachiage", "Maesabaki", "Read the Move"} and opponent.temporary_zone:
        priority = {
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

    if card.name in {"Katasukashi", "Hatakikomi", "Kirikaeshi"}:
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




def _context_variant(base: EffectContext, **updates: object) -> EffectContext:
    choices = dict(base.choices or {})
    choices.update(updates)
    return EffectContext(comparison=base.comparison, choices=choices)


def _contexts_for_card(
    state: BoutState,
    side: Side,
    card: Card,
    comparison: TachiaiComparison,
) -> list[EffectContext]:
    """Return meaningful deterministic choice variants for one card."""
    base = _context_for_card(state, side, card, comparison)
    opponent = state.opponent(side)
    fighter = state.fighter(side)

    if card.name.startswith(("R20:", "R21:")):
        # Both experimental gauntlets use the same deterministic AI choice
        # enumeration, without changing normal V5 card evaluation.
        if card.name.startswith("R21:"):
            from .r21_variant_rules import arm_id
            variant = arm_id(card).replace("R21-", "", 1)
        else:
            from .r20_variant_rules import arm_id
            variant = arm_id(card)
        family, number = variant.split("-", 1)
        if family in {"OKD", "OKT"}:
            return [
                _context_variant(base, conversion="position_to_momentum"),
                _context_variant(base, conversion="momentum_to_position"),
            ]
        if family == "HAT" or variant == "KAT-0":
            return [
                _context_variant(base, use_optional=False),
                _context_variant(base, use_optional=True),
            ]
        if family == "UWD":
            return [
                _context_variant(base, discard_for_grip=False),
                _context_variant(base, discard_for_grip=True),
            ]
        if family == "KOT":
            return [
                _context_variant(base, cycle_if_no_grip=False),
                _context_variant(base, cycle_if_no_grip=True),
            ]
        return [base]

    if card.name in {"Driving Force — Power Payoff", "Crushing Pressure — Power Crusher"}:
        eligible = fighter.power >= 7
        if card.name == "Crushing Pressure — Power Crusher":
            eligible = eligible and (fighter.power - opponent.power >= 3)
        effect_mode = "power_payoff" if card.name == "Driving Force — Power Payoff" else "power_crusher"
        return ([_context_variant(base, mode=effect_mode), _context_variant(base, mode="draw")]
                if eligible else [_context_variant(base, mode="draw")])

    if card.name in {"Okuridashi", "Okuritaoshi"}:
        return [
            _context_variant(base, mode="position_to_momentum"),
            _context_variant(base, mode="momentum_to_position"),
        ]

    if card.name == "Uwatedashinage":
        options = [_context_variant(base, discard_for_grip=False)]
        if fighter.hand or fighter.draw_pile:
            options.append(_context_variant(
                base, discard_for_grip=True,
                hand_index=_best_hand_index(state, side, prefer_discard=True),
            ))
        return options

    if card.name == "Katasukashi":
        if fighter.discard_pile:
            return [_context_variant(base, discard_index=_best_discard_index(state, side))]
        return [base]

    if card.name == "Tsuki":
        grips = []
        if opponent.left_grip is not GripState.NONE:
            grips.append("left")
        if opponent.right_grip is not GripState.NONE:
            grips.append("right")
        if len(grips) > 1:
            return [_context_variant(base, grip=grip) for grip in grips]

    if card.name == "Headlong Charge":
        return [
            _context_variant(base, sacrifice_kimarite=i)
            for i in range(len(fighter.kimarite_zone))
        ]

    if card.name == "Pull":
        return [base]

    if card.name in {"Kachiage", "Maesabaki", "Read the Move"} and opponent.temporary_zone:
        variants = [_context_variant(base, temporary_index=index, mode="remove")
                    for index in range(len(opponent.temporary_zone))]
        if card.name == "Read the Move":
            variants.append(_context_variant(base, mode="draw"))
        return variants

    if card.name == "Ottsuke":
        variants: list[EffectContext] = [_context_variant(base, mode="draw") ]

        grips = []
        if opponent.left_grip is not GripState.NONE:
            grips.append("left")
        if opponent.right_grip is not GripState.NONE:
            grips.append("right")
        variants.extend(
            _context_variant(base, mode="reduce_grip", grip=grip)
            for grip in grips
        )

        temp_targets = [
            instance
            for instance in opponent.temporary_zone
            if instance.card.name in {
                "Attempt Two-Handed Grip",
                "Attempt Deep Outside Grip",
                "Attempt Deep Inside Grip",
                "Kannuki",
                "Morozashi",
            }
        ]
        kimarite_targets = [
            target
            for target in opponent.kimarite_zone
            if target.name in {
                "Yorikiri", "Yoritaoshi", "Katasukashi", "Tottari",
                "Uwatenage", "Hikiotoshi", "Tsuridashi", "Kotenage",
                "Abisetaoshi",
            }
        ]
        total_targets = len(temp_targets) + len(kimarite_targets)
        variants.extend(
            _context_variant(
                base,
                mode="remove_card",
                card_target=index,
            )
            for index in range(total_targets)
        )

        if variants:
            return variants

    if card.name in {"Katasukashi", "Hikiotoshi", "Hatakikomi", "Tsukiotoshi"}:
        return [
            _context_variant(base, use_optional=False),
            _context_variant(base, use_optional=True),
        ]

    if card.name == "Kotenage" and effective_total_grip(
        state, state.opponent_side(side)
    ) == 0:
        return [
            _context_variant(base, cycle_if_no_grip=False),
            _context_variant(base, cycle_if_no_grip=True),
        ]

    return [base]


def _at_least(value: int, target: int) -> float:
    if target <= 0:
        return 1.0
    return max(0.0, min(1.0, value / target))


def _at_most(value: int, target: int) -> float:
    if value <= target:
        return 1.0
    distance = value - target
    return max(0.0, 1.0 - distance / 3.0)


def _nonnegative(value: int) -> float:
    if value >= 0:
        return 1.0
    return max(0.0, 1.0 + value / 3.0)


def kimarite_progress(state: BoutState, side: Side, card: Card) -> float:
    """Return 0..1 progress toward one live Kimarite."""
    if card.name.startswith("R21:"):
        from .r21_variant_rules import arm_id, variant_progress
        return variant_progress(state, side, arm_id(card))
    if card.name.startswith("R20:"):
        from .r20_variant_rules import arm_id, variant_progress
        return variant_progress(state, side, arm_id(card))
    fighter = state.fighter(side)
    opponent = state.opponent(side)
    momentum = relative_momentum(state, side)
    position = relative_position(state, side)
    grip = effective_total_grip(state, side)
    power_adv = fighter.power - opponent.power

    hand_adv = len(fighter.hand) - len(opponent.hand)
    reversal = 1.0 if fighter.successful_reversal_this_turn else 0.0
    if card.name == "Yorikiri":
        parts = [_at_least(grip, 1), _at_least(momentum, 1), _at_least(position, 2)]
    elif card.name == "Oshidashi":
        parts = [_at_least(momentum, 2), _at_least(position, 2)]
    elif card.name == "Tsukidashi":
        parts = [_at_least(position, 2), _at_least(fighter.cards_played_this_turn, 3)]
    elif card.name == "Oshitaoshi":
        parts = [_at_least(momentum, 1), _at_least(position, 1), _at_least(fighter.power, 8)]
    elif card.name == "Yoritaoshi":
        parts = [_at_least(grip, 1), _at_least(position, 2), _at_least(power_adv, 2)]
    elif card.name == "Katasukashi":
        parts = [1.0 if effective_total_grip(state, state.opponent_side(side)) == 0 else 0.0,
                 _at_least(momentum, 2), _at_least(hand_adv, 5)]
    elif card.name == "Tsukiotoshi":
        parts = [1.0 if grip == 0 else 0.0, _at_least(momentum, 1), _at_most(power_adv, -3),
                 1.0 if opponent.unstable else 0.0]
    elif card.name == "Tottari":
        parts = [1.0 if grip == 0 else 0.0, 1.0 if fighter.opponent_grip_reduced_this_turn else 0.0,
                 _at_least(len(opponent.discard_pile), 7)]
    elif card.name == "Uwatenage":
        parts = [1.0 if fighter.left_grip is GripState.DEEP and grip > 0 else 0.0,
                 _at_least(momentum, 1), _nonnegative(position)]
    elif card.name == "Shitatenage":
        parts = [1.0 if fighter.right_grip is GripState.DEEP and grip > 0 else 0.0,
                 _at_least(momentum, 1), _nonnegative(position)]
    elif card.name == "Hatakikomi":
        parts = [_at_most(momentum, -2), _at_least(fighter.power, 6)]
    elif card.name == "Hikiotoshi":
        parts = [_at_most(momentum, -2), _nonnegative(position), _at_least(grip, 1)]
    elif card.name == "Tsukitaoshi":
        parts = [_at_least(momentum, 2), _at_least(fighter.cards_played_this_turn, 3)]
    elif card.name == "Tsuridashi":
        parts = [_at_least(grip, 3), _nonnegative(position), _at_least(fighter.power, 6)]
    elif card.name == "Kotenage":
        parts = [1.0 if effective_total_grip(state, state.opponent_side(side)) == 0 else 0.0,
                 _at_least(momentum, 1), _at_least(len(fighter.hand), 5)]
    elif card.name == "Abisetaoshi":
        parts = [_at_least(grip, 2), _at_least(fighter.power, 10)]
    elif card.name == "Kirikaeshi":
        parts = [_at_most(power_adv, -3), 1.0 if not fighter.unstable else 0.0,
                 1.0 if opponent.unstable else 0.0, _at_least(momentum, 2)]
    elif card.name == "Okuridashi":
        parts = [reversal, _at_least(position, 1), _at_least(momentum, 1)]
    elif card.name == "Okuritaoshi":
        parts = [reversal, _nonnegative(position), _at_least(momentum, 2)]
    elif card.name == "Sukuinage":
        parts = [1.0 if grip == 0 else 0.0, _at_least(momentum, 2), _at_least(hand_adv, 5)]
    elif card.name == "Utchari":
        parts = [1.0 if fighter.gained_momentum_this_turn else 0.0, _at_most(position, -3)]
    elif card.name == "Uwatedashinage":
        parts = [1.0 if fighter.left_grip is not GripState.NONE and grip > 0 else 0.0,
                 _at_least(momentum, 1), _at_most(power_adv, -5)]
    else:
        return 0.0

    return sum(parts) / len(parts)


def live_kimarite_progress(state: BoutState, side: Side) -> float:
    cards = state.fighter(side).kimarite_zone
    if not cards:
        return 0.0
    values = sorted(
        (kimarite_progress(state, side, card) for card in cards),
        reverse=True,
    )
    # Focus on the best live path, but give a little value to a second route.
    return values[0] + (values[1] * 0.15 if len(values) > 1 else 0.0)


def next_turn_kimarite_state(state: BoutState, side: Side) -> BoutState:
    """Clone state with that wrestler's turn-local flags reset."""
    trial = deepcopy(state)
    fighter = trial.fighter(side)
    fighter.cards_played_this_turn = 0
    fighter.played_this_turn.clear()
    fighter.lost_position_this_turn = False
    fighter.opponent_grip_reduced_this_turn = False
    fighter.gained_push_this_turn = False
    fighter.gained_momentum_this_turn = False
    return trial


def score_state(state: BoutState, side: Side) -> float:
    if state.winner is side:
        return 1_000_000.0
    if state.winner is state.opponent_side(side):
        return -1_000_000.0

    fighter = state.fighter(side)
    opponent = state.opponent(side)

    score = 0.0
    score += relative_momentum(state, side) * 8
    score += relative_position(state, side) * 10
    score += (fighter.power - opponent.power) * 3
    score += effective_total_grip(state, side) * 4
    score -= effective_total_grip(state, state.opponent_side(side)) * 3
    score += len(fighter.hand) * 1.5
    score -= len(opponent.hand) * 0.5
    score += fighter.plays_remaining * 0.5
    score += 22 if opponent.unstable else 0
    score -= 24 if fighter.unstable else 0
    score += 8 * sum(x.card.name in {"Denshamichi", "Spin Away", "Nekodamashi", "Henka", "Kannuki"} for x in fighter.temporary_zone)

    # Shiko Stomp prevents a future opposing negative effect and persists
    # until consumed. Without a state value, one-step AI treats this delayed
    # defense as a wasted Play. Additional copies have diminishing value.
    stomp_count = sum(t.card.name == "Shiko Stomp" for t in fighter.temporary_zone)
    opposing_stomps = sum(t.card.name == "Shiko Stomp" for t in opponent.temporary_zone)
    score += min(stomp_count, 1) * 17 + max(0, stomp_count - 1) * 5
    score -= min(opposing_stomps, 1) * 13 + max(0, opposing_stomps - 1) * 4

    own_progress = live_kimarite_progress(state, side)
    opponent_side = state.opponent_side(side)
    opponent_future = next_turn_kimarite_state(state, opponent_side)
    opponent_progress = live_kimarite_progress(
        opponent_future,
        opponent_side,
    )
    score += own_progress * 75
    score -= opponent_progress * 55

    # A satisfied own Kimarite is decisive at this turn's check. Opponent
    # threat is evaluated after clearing turn-local conditions that will reset
    # before their next start-of-turn check.
    try:
        if satisfied_kimarite(state, side):
            score += 100_000
        if satisfied_kimarite(opponent_future, opponent_side):
            score -= 5_000
    except KeyError:
        pass

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

        for context in _contexts_for_card(state, side, card, comparison):
            trial = deepcopy(state)
            trial_card = next(
                c for c in trial.fighter(side).hand
                if c.card_id == card.card_id
            )
            try:
                play_card(trial, side, trial_card, context=context)
            except (
                IllegalPlay,
                ChoiceRequired,
                NotImplementedError,
                KeyError,
                ValueError,
            ):
                continue

            plays.append(
                AIPlay(
                    card=card,
                    context=context,
                    score=score_state(trial, side),
                )
            )

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

        # Candidate generation used the current live state, so the selected
        # context is valid for this immediate play.
        try:
            play_card(state, side, choice.card, context=choice.context)
        except (IllegalPlay, ChoiceRequired, NotImplementedError, KeyError, ValueError):
            break
        played.append(choice.card.name)

    return played
