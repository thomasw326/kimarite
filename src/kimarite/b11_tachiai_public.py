"""Public pre-Tachiai view: the opponent's opening is secret until commit.

Keep this module separate from the ordinary post-Tachiai snapshot because
that snapshot legitimately contains revealed prepared cards and orb totals.
A pending decision must not accidentally serialize a BoutState, Wrestler,
full opening comparison or even the engine's pre-resolution event log.
"""
from __future__ import annotations

from .b10_card_info import card_info
from .b11_tachiai_phase import PendingPlayerTachiai


def pending_tachiai_snapshot(phase: PendingPlayerTachiai, human_name: str,
                             opponent_name: str) -> dict:
    """Construct an explicit allow-list response, never a redacted full state."""
    if not phase.pending:
        raise ValueError("Tachiai is no longer pending.")
    return {
        "phase": "choose_tachiai",
        "finished": False,
        "human": {"name": human_name},
        "opponent": {"name": opponent_name},
        "tachiai_choice": {
            "cards": [card_info(c) for c in phase.opening.cards],
            "allowed_commits": [0, 1, 2, 3],
        },
        "opening": None,
        "events": [],
        "selection": None,
        "legal_plays": [],
        "can_end_turn": False,
    }
