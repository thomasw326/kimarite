"""V5 style-aware Exchange choices: win, survive, then personal preference.

Opt-in: existing V4.5 tactical and personality decision makers are unchanged.
"""
from __future__ import annotations

from copy import deepcopy

from .ai import AIPlay, candidate_plays, relative_momentum, relative_position, score_state
from .effects import ChoiceRequired, IllegalPlay
from .models import BoutState, Side
from .playing import play_card
from .styles_v5 import STYLES, preference_bonus
from .tachiai import TachiaiComparison


def choose_style_play(state: BoutState, side: Side, comparison: TachiaiComparison, style: str) -> AIPlay | None:
    profile = STYLES[style]
    plays = candidate_plays(state, side, comparison)
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
        affinity = preference_bonus(profile, candidate.card.name) * 4
        scored.append((
            tier, candidate.score + danger_score + affinity,
            preference_bonus(profile, candidate.card.name), -candidate.card.card_id,
            candidate,
        ))

    if not scored:
        return None
    selected = max(scored, key=lambda item: item[:4])
    if selected[0] < 0 or (selected[0] < 3 and selected[1] < current - 100):
        return None
    return selected[-1]


def play_style_turn(
    state: BoutState, side: Side, comparison: TachiaiComparison, style: str, *, max_cards: int = 20
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
