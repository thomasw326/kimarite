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
    seed: int = 20261021
    created_stats: dict[str, int] | None = None
    drafted_deck: list[str] | None = None

    @classmethod
    def start(cls, human: str, opponent: str, names: list[str], *, seed: int = 20261021, created_stats: dict[str, int] | None = None, drafted_deck: list[str] | None = None) -> "PendingB11Session":
        if human not in roster() or opponent not in roster():
            raise ValueError("Both wrestlers must be in the approved B10 roster.")
        if not isinstance(names, list):
            raise ValueError("B11 opening requires three selected card names.")
        if created_stats is not None:
            if not isinstance(created_stats, dict) or set(created_stats) != {"power", "technique", "spirit"} or sorted(created_stats.values(), key=str) != [0, 1, 2]:
                raise ValueError("Created wrestler stats must be an exact 2-1-0 distribution.")
        records = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))["decks"]
        if drafted_deck is not None:
            from .b11_player_draft import AVAILABLE, MAX_KIMARITE
            if (not isinstance(drafted_deck, list) or len(drafted_deck) != 28
                    or len(set(drafted_deck)) != 28
                    or any(n not in AVAILABLE for n in drafted_deck)
                    or not 3 <= sum(AVAILABLE[n].is_kimarite for n in drafted_deck) <= MAX_KIMARITE):
                raise ValueError("Invalid B11 drafted deck; require 28 distinct cards and 3–8 Kimarite.")
        deck = [card_by_name(name) for name in (drafted_deck if drafted_deck is not None else records[human]["cards"])]
        opening = PlayerOpening.from_names(deck, names)
        return cls(human, opponent, PendingPlayerTachiai(opening), seed=seed, created_stats=created_stats, drafted_deck=drafted_deck)

    def confirm(self, indices: list[int]) -> dict[str, Any]:
        """Record a one-time human decision; actual resolution remains gated."""
        if not isinstance(indices, list):
            raise ValueError("Commitment must be a list of slot indices.")
        self.phase.choose(indices)
        return self.snapshot()

    def prepare_resolution(self):
        """Build the private exact-card handoff only after commitment.

        Do not serialize this object to clients: it includes hidden deck cards.
        The live multi-effect resolver will consume it when implemented.
        """
        if self.phase.pending:
            raise ValueError("Commit Tachiai before preparing its resolution.")
        from .b11_tachiai_resolution import prepare_human_tachiai
        records = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))["decks"]
        deck = [card_by_name(name) for name in (self.drafted_deck if self.drafted_deck is not None else records[self.human]["cards"])]
        return prepare_human_tachiai(self.phase.opening, self.phase.decision, deck)

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
