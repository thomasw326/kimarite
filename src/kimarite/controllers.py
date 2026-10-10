"""Decision-controller boundary for AI-vs-AI and future human-vs-AI bouts.

A controller receives the current mutable bout state, the acting side, and
the immutable Tachiai comparison. It may submit legal actions through
kimarite.playing.play_card (which validates each play), or pass.

This initial interface operates at whole-turn granularity for compatibility
with the current simulator. An interactive UI will eventually require a
pause/resume action-by-action session API; that is deliberately not claimed
or implemented here.
"""
from __future__ import annotations

from collections.abc import Callable

from .ai import play_ai_turn
from .models import BoutState, Side
from .tachiai import TachiaiComparison


TurnController = Callable[[BoutState, Side, TachiaiComparison], object]


def ai_controller(
    state: BoutState, side: Side, comparison: TachiaiComparison
) -> None:
    """Use the existing tactical AI without altering its decisions."""
    play_ai_turn(state, side, comparison)
