"""Personality-first Exchange AI, separate from the tactical baseline.

Priorities dominate ordinary card selection; tactical intelligence is reserved
for immediate wins, avoiding catastrophically bad moves, and final ties.
"""
from __future__ import annotations

from .ai import AIPlay, candidate_plays, score_state
from .effects import ChoiceRequired, IllegalPlay
from .models import BoutState, Side
from .playing import play_card
from .tachiai import TachiaiComparison


def choose_personality_play(
    state: BoutState, side: Side, comparison: TachiaiComparison,
) -> AIPlay | None:
    plays = candidate_plays(state, side, comparison)
    if not plays:
        return None

    current_score = score_state(state, side)
    # Don't willingly lose immediately or take a catastrophically harmful move.
    safe = [
        play for play in plays
        if play.score > -1_000_000 and play.score >= current_score - 100
    ]
    if not safe:
        return None

    # Winning this turn outranks personal style.
    winning = [play for play in safe if play.score >= 1_000_000]
    candidates = winning or safe

    wrestler = state.fighter(side).wrestler
    return max(
        candidates,
        key=lambda play: (
            play.card.orbs(wrestler.primary),
            play.card.orbs(wrestler.secondary),
            play.card.orbs(wrestler.tertiary),
            play.score,
            -play.card.card_id,
        ),
    )


def play_personality_turn(
    state: BoutState, side: Side, comparison: TachiaiComparison,
    *, max_cards: int = 20,
) -> list[str]:
    played: list[str] = []
    for _ in range(max_cards):
        if state.winner is not None or state.fighter(side).plays_remaining <= 0:
            break
        choice = choose_personality_play(state, side, comparison)
        if choice is None:
            break
        try:
            play_card(state, side, choice.card, context=choice.context)
        except (IllegalPlay, ChoiceRequired, NotImplementedError, KeyError, ValueError):
            break
        played.append(choice.card.name)
    return played
