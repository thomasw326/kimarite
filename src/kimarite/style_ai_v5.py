"""V5 style-aware Exchange choices: win, survive, then personal preference.

Opt-in: existing V4.5 tactical and personality decision makers are unchanged.
"""
from __future__ import annotations

from copy import deepcopy

from .ai import AIPlay, candidate_plays, relative_momentum, relative_position, score_state
from .effects import ChoiceRequired, IllegalPlay
from .models import BoutState, Side
from .playing import play_card
from .styles_v5 import STYLES
from .affinity_v5 import affinity as card_affinity
from .tachiai import TachiaiComparison


# Draw + Play cards can be held across turns. Their main tactical use is
# extending a later sequence to four played cards for the Tsuki Kimarite.
DRAW_AND_PLAY = frozenset({"Oshi", "Tsuki", "Tsuppari", "Power Water Cantrip"})


def _four_card_setup_hold_value(state: BoutState, side: Side, card_name: str) -> float:
    """Reward retaining a cycling card when a four-card finish is within reach.

    This estimates next-turn potential rather than looking into a hidden draw.
    Immediate wins are still scored in a higher tier by choose_style_play.
    """
    if card_name not in DRAW_AND_PLAY:
        return 0.0
    fighter = state.fighter(side)
    if len(fighter.draw_pile) == 0:
        return 0.0
    kimarite = {card.name for card in fighter.kimarite_zone}
    momentum = relative_momentum(state, side)
    position = relative_position(state, side)
    has_tsukidashi = "Tsukidashi" in kimarite and position >= 1
    has_tsukitaoshi = "Tsukitaoshi" in kimarite and momentum >= 1
    if not (has_tsukidashi or has_tsukitaoshi):
        return 0.0
    # If already partway into a four-card sequence this turn, let the
    # existing win/progress scorer prioritize finishing it immediately.
    if fighter.cards_played_this_turn >= 2:
        return 0.0
    return 35.0 if position >= 2 or momentum >= 2 else 22.0



def neutral_development_value(before: BoutState, after: BoutState, side: Side, card_name: str) -> float:
    """State-3 resource development, independent of archetype preferences.

    Score real state changes, not printed effects that fail to resolve.
    Later strategic modes still use the original tactical evaluator.
    """
    from .rules import effective_total_grip
    a, b = before.fighter(side), after.fighter(side)
    foe_a, foe_b = before.opponent(side), after.opponent(side)
    old_grip = effective_total_grip(before, side)
    new_grip = effective_total_grip(after, side)
    push = relative_position(after, side) - relative_position(before, side)
    momentum = relative_momentum(after, side) - relative_momentum(before, side)
    power = b.power - a.power
    grip_gain = max(0, new_grip - old_grip)
    value = 10 * push + 7 * momentum + 5 * power
    if grip_gain:
        value += (12 if old_grip == 0 else 4) + 4 * max(0, grip_gain - 1)
    elif new_grip < old_grip:
        value -= 8 * (old_grip - new_grip)
    value += 3 * max(0, effective_total_grip(before, before.opponent_side(side)) -
                     effective_total_grip(after, after.opponent_side(side)))
    new_stomps = sum(x.card.name == "Shiko Stomp" for x in b.temporary_zone)
    old_stomps = sum(x.card.name == "Shiko Stomp" for x in a.temporary_zone)
    if new_stomps > old_stomps:
        value += 12 if old_stomps == 0 else 3
    removed = [x.card.name for x in foe_a.temporary_zone
               if x.card.name not in [y.card.name for y in foe_b.temporary_zone]]
    if removed:
        # Count remaining useful effects, not merely Temporary names.
        value += 18 * len(removed)  # Opportunity to disrupt may expire.
    # Favor early card discovery only when Plays remain to exploit it.
    draw_delta = len(b.hand) - len(a.hand) + 1  # played card leaves hand
    if draw_delta > 0:
        # Only reward information if there are Plays to use it.
        extra = 6 if a.plays_remaining >= 3 else 4 if a.plays_remaining == 2 else 0
        value += draw_delta * (2 + extra)
    gained_play = b.plays_remaining - (a.plays_remaining - 1)
    if gained_play > 0:
        remaining_useful = any(c.name not in {"Injury"} for c in b.hand)
        value += 7 * gained_play if remaining_useful else 0
    # An ordinary Temporary only earns a setup credit if its effect remains.
    temporary_added = len(b.temporary_zone) - len(a.temporary_zone)
    if temporary_added > 0 and card_name != "Shiko Stomp":
        value += min(temporary_added, 2) * 2
    # Oshi's required extra discard is a real opportunity cost.
    # Its Draw offsets the hand count but does not restore the chosen card.
    if card_name == "Oshi" and len(a.hand) > 1:
        value -= 10
    return value


def neutral_foregone_benefit(before: BoutState, side: Side, card_name: str) -> float:
    """Penalty for spending a conditional Grip card before using its better payoff.

    Applies only when another card currently in hand can first establish Grip
    and there are enough Plays for both actions. This is deliberately a local
    sequencing estimate, not a second penalty after multi-play lookahead.
    """
    from .rules import effective_total_grip
    if effective_total_grip(before, side) > 0:
        return 0.0
    payoff = {"Yori": 10, "Gaburi": 7, "Tsuri": 5}.get(card_name)
    if payoff is None or before.fighter(side).plays_remaining < 2:
        return 0.0
    # Other flexible Grip cards can establish Grip as the first play.
    setup_names = {"Yori", "Gaburi", "Tsuri", "Gain Left Grip",
                   "Gain Right Grip", "Uwate", "Shitate"}
    setup_available = any(c.name in setup_names and c.name != card_name
                          for c in before.fighter(side).hand)
    if not setup_available:
        return 0.0
    # Opening with this card forfeits the higher conditional payoff.
    # Relative to Tsuri's post-Grip Power (5), Yori sacrifices 5 points,
    # while Gaburi sacrifices 2. Other setup cards do not require a penalty.
    alternative_payoffs = [v for name, v in {"Yori": 10, "Gaburi": 7, "Tsuri": 5}.items()
                           if name != card_name and
                           any(c.name == name for c in before.fighter(side).hand)]
    if alternative_payoffs:
        return max(0.0, payoff - min(alternative_payoffs))
    # A dedicated Grip setup card can be spent first without consuming
    # the flexible card's conditional payoff.
    return float(payoff)


def choose_style_play(state: BoutState, side: Side, comparison: TachiaiComparison, style: str | None) -> AIPlay | None:
    if style is not None and style not in STYLES:
        raise ValueError(f"Unknown V5 style: {style}")
    plays = candidate_plays(state, side, comparison)
    # Never choose Headlong Charge decline when a Kimarite can be sacrificed.
    if state.fighter(side).kimarite_zone:
        plays = [p for p in plays if p.card.name != "Headlong Charge"
                 or p.context.choice("sacrifice_kimarite") is not None]
    # Reset to Neutral clears both Temporary zones. Never play it after
    # another card has been played this turn, to preserve our own setups.
    if state.fighter(side).cards_played_this_turn > 0:
        plays = [p for p in plays if p.card.name != "Reset to Neutral"]
    if not plays:
        return None

    before_position = relative_position(state, side)
    before_momentum = relative_momentum(state, side)
    current = score_state(state, side)
    scored = []

    for candidate in plays:
        trial = deepcopy(state)
        card = next(c for c in trial.fighter(side).hand if c.card_id == candidate.card.card_id)
        try:
            play_card(trial, side, card, context=candidate.context)
        except (ChoiceRequired, IllegalPlay, ValueError, KeyError, NotImplementedError):
            continue
        if trial.winner is side:
            tier = 3
        elif candidate.card.name == "Reset to Neutral" and state.fighter(side).cards_played_this_turn == 0 and trial.winner is None:
            # If we are using Reset, do it before generating new Temporaries.
            tier = 2
        elif trial.winner is not None or candidate.score <= -1_000_000:
            tier = -1
        else:
            tier = 1

        after_position = relative_position(trial, side)
        after_momentum = relative_momentum(trial, side)
        danger_score = 0
        if before_position <= -2 or before_momentum <= -2:
            danger_score += 45 * (after_position - before_position)
            danger_score += 30 * (after_momentum - before_momentum)
        if after_position <= -2:
            danger_score -= 45 * (-1 - after_position)
        if after_momentum <= -2:
            danger_score -= 30 * (-1 - after_momentum)

        # Affinity is a preference after survival, not an instruction to lose.
        # Current 61-card six-axis ratings, including new Power payoff cards.
        # Scaled like the former rank bonus while preserving tactical scoring.
        affinity = card_affinity(style, candidate.card.name) * 4 if style is not None else 0
        setup_hold = _four_card_setup_hold_value(state, side, candidate.card.name)
        # Morotezuki is an opener: each later play is +1 Push. Reward only
        # when another play remains; otherwise retain it for a future turn.
        opener_bonus = 0
        if candidate.card.name == "Morotezuki":
            if state.fighter(side).cards_played_this_turn == 0 and state.fighter(side).plays_remaining >= 2:
                opener_bonus = 34
            else:
                setup_hold += 35
        # Only use neutral development weights when neither wrestler is under
        # material pressure and there is no immediate finishing opportunity.
        neutral = (abs(before_position) < 2 and abs(before_momentum) < 2
                   and abs(state.fighter(side).power - state.opponent(side).power) < 3
                   and trial.winner is None)
        neutral_bonus = neutral_development_value(state, trial, side, candidate.card.name) if neutral else 0
        # State 3 uses its OWN scale. Do not add these values to score_state,
        # whose unrelated grip/progress/unstable weights would dominate them.
        # Style affinity is deliberately excluded here until calibrated to
        # the agreed neutral decisions and actual deck win conditions.
        evaluation = (neutral_bonus + opener_bonus - neutral_foregone_benefit(state, side, candidate.card.name) if neutral
                      else candidate.score + danger_score + affinity + opener_bonus - setup_hold)
        scored.append((
            tier, evaluation,
            (card_affinity(style, candidate.card.name) if style is not None else 0), -candidate.card.card_id,
            candidate,
        ))

    if not scored:
        return None
    selected = max(scored, key=lambda item: item[:4])
    if selected[0] < 0 or (selected[0] < 3 and selected[1] < -100):
        return None
    return selected[-1]


def play_style_turn(
    state: BoutState, side: Side, comparison: TachiaiComparison, style: str | None, *, max_cards: int = 20
) -> list[str]:
    played = []
    for _ in range(max_cards):
        if state.winner is not None or state.fighter(side).plays_remaining <= 0:
            break
        choice = choose_style_play(state, side, comparison, style)
        if choice is None:
            break
        try:
            play_card(state, side, choice.card, context=choice.context)
        except (IllegalPlay, ChoiceRequired, KeyError, ValueError, NotImplementedError):
            break
        played.append(choice.card.name)
    return played
