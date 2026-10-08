from __future__ import annotations

from dataclasses import dataclass

from .ai import play_ai_turn
from .models import BoutState, Side
from .setup import BoutConfig, PreparedBout, create_prepared_bout
from .turns import end_exchange_turn, start_exchange_turn


@dataclass(frozen=True)
class SimulationResult:
    state: BoutState
    completed: bool
    turns: int
    unsupported_reason: str | None = None


def run_bout(
    config: BoutConfig,
    *,
    max_turns: int = 100,
) -> SimulationResult:
    prepared: PreparedBout = create_prepared_bout(config)
    state = prepared.state
    comparison = prepared.comparison

    if state.winner is not None:
        return SimulationResult(state=state, completed=True, turns=0)

    if state.active_side is None:
        return SimulationResult(
            state=state,
            completed=False,
            turns=0,
            unsupported_reason="No active wrestler was determined.",
        )

    for _ in range(max_turns):
        side: Side = state.active_side

        try:
            start_exchange_turn(state, side, comparison)
        except NotImplementedError as exc:
            return SimulationResult(
                state=state,
                completed=False,
                turns=state.turn_number,
                unsupported_reason=str(exc),
            )

        if state.winner is not None:
            return SimulationResult(
                state=state,
                completed=True,
                turns=state.turn_number,
            )

        play_ai_turn(state, side, comparison)

        if state.winner is not None:
            return SimulationResult(
                state=state,
                completed=True,
                turns=state.turn_number,
            )

        try:
            end_exchange_turn(state, side)
        except NotImplementedError as exc:
            return SimulationResult(
                state=state,
                completed=False,
                turns=state.turn_number,
                unsupported_reason=str(exc),
            )

        if state.winner is not None:
            return SimulationResult(
                state=state,
                completed=True,
                turns=state.turn_number,
            )

    return SimulationResult(
        state=state,
        completed=False,
        turns=state.turn_number,
        unsupported_reason=f"Turn limit {max_turns} reached.",
    )
