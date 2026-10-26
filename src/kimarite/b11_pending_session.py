"""B11 pending opening preview, deliberately separate from Classic live sessions.

The decision endpoint is intentionally not enabled until multi-card Tachiai
resolution is complete. No AI state, opposing opening or private seed is
created/serialized during this pre-commit phase.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .b10_human_session import ROSTER_PATH, roster
from .b11_player_opening import PlayerOpening
from .b11_tachiai_phase import PendingPlayerTachiai
from .b11_tachiai_public import pending_tachiai_snapshot
from .catalog import card_by_name


@dataclass
class PendingB11Session:
    human: str
    opponent: str
    phase: PendingPlayerTachiai

    @classmethod
    def start(cls, human: str, opponent: str, names: list[str]) -> "PendingB11Session":
        if human not in roster() or opponent not in roster():
            raise ValueError("Both wrestlers must be in the approved B10 roster.")
        if not isinstance(names, list):
            raise ValueError("B11 opening requires three selected card names.")
        records = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))["decks"]
        deck = [card_by_name(name) for name in records[human]["cards"]]
        opening = PlayerOpening.from_names(deck, names)
        return cls(human, opponent, PendingPlayerTachiai(opening))

    def confirm(self, indices: list[int]) -> dict[str, Any]:
        """Record a one-time human decision; actual resolution remains gated."""
        if not isinstance(indices, list):
            raise ValueError("Commitment must be a list of slot indices.")
        self.phase.choose(indices)
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        if self.phase.pending:
            return pending_tachiai_snapshot(self.phase, self.human, self.opponent)
        decision = self.phase.decision
        from .b10_card_info import card_info
        return {
            "phase": "tachiai_resolution_pending",
            "finished": False,
            "human": {"name": self.human},
            "opponent": {"name": self.opponent},
            "tachiai_choice": {
                "cards": [card_info(c) for c in decision.allocated],
                "committed_indices": list(decision.indices),
                "committed": [card_info(c) for c in decision.committed],
                "retained": [card_info(c) for c in decision.retained],
            },
            "opening": None,
            "events": [],
            "selection": None,
            "legal_plays": [],
            "can_end_turn": False,
        }
