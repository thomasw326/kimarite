"""Controller seam shared by automated bouts and future interactive play.

The engine owns rules and legality; a controller decides which legal actions
to request during its side's Exchange turn. This compatibility-level interface
handles complete turns. It intentionally does not yet implement pause/resume,
an observation filter, or individual human selection prompts.
"""
from __future__ import annotations

from collections.abc import Callable

from .ai import play_ai_turn
from .models import BoutState, Side
from .personality_ai import play_personality_turn
from .tachiai import TachiaiComparison


TurnController = Callable[[BoutState, Side, TachiaiComparison], object]


def tactical_controller(
    state: BoutState, side: Side, comparison: TachiaiComparison
) -> None:
    """Existing tactical AI behavior, with no new rule interpretations."""
    play_ai_turn(state, side, comparison)


def personality_controller(
    state: BoutState, side: Side, comparison: TachiaiComparison
) -> None:
    """Existing personality AI behavior, with no change to selection."""
    play_personality_turn(state, side, comparison)


def controller_for_mode(ai_mode: str) -> TurnController:
    """Resolve the legacy AI option through a common controller boundary."""
    if ai_mode == "tactical":
        return tactical_controller
    if ai_mode == "personality":
        return personality_controller
    raise ValueError(f"Unknown AI mode: {ai_mode}")
