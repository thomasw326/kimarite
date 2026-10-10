"""Experimental V5 Sumo Style head-to-head simulator.

Uses the production shared rules engine, with new opt-in style profiles.
Does not alter the established 30-wrestler Big Test.
"""
from __future__ import annotations

from .models import BoutState, Side, Stat
from .simulate import SimulationResult
from .style_ai_v5 import play_style_turn
from .style_builds_v5 import build_style
from .tachiai import compare_tachiai, first_exchange_side
from .tachiai_effects import resolve_prepared_tachiai
from .turns import apply_initial_power, end_exchange_turn, start_exchange_turn


def run_style_bout(
    style_a: str, style_b: str, *,
    seed: int = 0, max_turns: int = 100, difficulty: int = 0,
) -> SimulationResult:
    first = build_style(style_a, seed=seed, ranking=1, difficulty=difficulty)
    second = build_style(style_b, seed=seed + 1009, ranking=2, difficulty=difficulty)
    state = BoutState(first.fighter, second.fighter)
    comp = compare_tachiai(first.fighter.wrestler, second.fighter.wrestler)
    apply_initial_power(state, comp)
    # R15 Headlong Charge: always sacrifice the first available Kimarite.
    opening_choices = {}
    for side in (Side.A, Side.B):
        fighter = state.fighter(side)
        if fighter.wrestler.prepared_tachiai_card.name == "Headlong Charge":
            opening_choices[side] = 0 if fighter.kimarite_zone else None
    resolve_prepared_tachiai(state, comp, sacrifice_choices=opening_choices)
    if state.winner is not None:
        return SimulationResult(state, True, 0)
    state.active_side = first_exchange_side(comp, first.fighter.wrestler, second.fighter.wrestler)

    for _ in range(max_turns):
        side = state.active_side
        if side is None:
            return SimulationResult(state, False, state.turn_number, "No active side")
        try:
            start_exchange_turn(state, side, comp)
            if state.winner is not None:
                break
            play_style_turn(state, side, comp, style_a if side is Side.A else style_b)
            if state.winner is not None:
                break
            end_exchange_turn(state, side)
            if state.winner is not None:
                break
        except (NotImplementedError, KeyError, ValueError) as exc:
            return SimulationResult(state, False, state.turn_number, str(exc))
    if state.winner is None:
        return SimulationResult(state, False, state.turn_number, f"Turn limit {max_turns} reached")
    return SimulationResult(state, True, state.turn_number)
