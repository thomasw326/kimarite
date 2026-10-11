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


def choose_style_play(state: BoutState, side: Side, comparison: TachiaiComparison, style: str | None) -> AIPlay | None:
    if style is not None and style not in STYLES:
        raise ValueError(f"Unknown V5 style: {style}")
    plays = candidate_plays(state, side, comparison)
    # Never choose Headlong Charge decline when a Kimarite can be sacrificed.
    if state.fighter(side).kimarite_zone:
        plays = [p for p in plays if p.card.name != "Headlong Charge"
                 or p.context.choice("sacrifice_kimarite") is not None]
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
        scored.append((
            tier, candidate.score + danger_score + affinity - setup_hold,
            (card_affinity(style, candidate.card.name) if style is not None else 0), -candidate.card.card_id,
            candidate,
        ))

    if not scored:
        return None
    selected = max(scored, key=lambda item: item[:4])
    if selected[0] < 0 or (selected[0] < 3 and selected[1] < current - 100):
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
