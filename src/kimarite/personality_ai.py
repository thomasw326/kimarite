"""LEGACY V4.5 personality-first Exchange AI. NOT FOR V5 STYLE BALANCE TESTING.

V5 15-style tests MUST use style_ai_v5.play_style_turn instead.

Priorities dominate ordinary card selection; tactical intelligence is reserved
for immediate wins, avoiding catastrophically bad moves, and final ties.
"""
from __future__ import annotations

from .ai import AIPlay, candidate_plays, score_state
from .effects import ChoiceRequired, IllegalPlay
from .models import BoutState, Side
from .playing import play_card
from .tachiai import TachiaiComparison


# Optional override for selection only; wrestler attributes and stats stay unchanged.
POWER_GRAPPLER_ORB_PRIORITY = False


def choose_personality_play(
    state: BoutState, side: Side, comparison: TachiaiComparison,
) -> AIPlay | None:
    plays = candidate_plays(state, side, comparison)
    if not plays:
        return None

    # Avoid voluntarily losing Position with either retreat card at our edge.
    # With a shared signed track, -3 relative Position is our own edge.
    if state.position * state.sign(side) <= -3:
        plays = [p for p in plays if p.card.name not in {"Use the Tawara", "Give Ground"}]
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
    if POWER_GRAPPLER_ORB_PRIORITY:
        from .models import Stat
        priorities = (Stat.POWER, Stat.TECHNIQUE, Stat.SPIRIT)
    else:
        priorities = (wrestler.primary, wrestler.secondary, wrestler.tertiary)
    return max(
        candidates,
        key=lambda play: (
            play.card.orbs(priorities[0]),
            play.card.orbs(priorities[1]),
            play.card.orbs(priorities[2]),
            play.score,
            -play.card.card_id,
        ),
    )


def play_personality_turn(
    state: BoutState, side: Side, comparison: TachiaiComparison,
    *, max_cards: int = 20,
) -> list[str]:
    from .styles_v5 import STYLES
    if state.fighter(side).wrestler.name in STYLES:
        raise RuntimeError("Obsolete orb-first personality AI forbidden for V5 styles: use style_ai_v5.play_style_turn")
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
