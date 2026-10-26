"""Server-authoritative pending player Tachiai decision.

This intentionally pauses *before* any Tachiai comparison or effect. The
session API must call resolve_once before progressing; committed cards are
never silently selected by the UI, and retained cards remain player-owned.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .b11_player_opening import PlayerOpening
from .models import Card


@dataclass(frozen=True)
class TachiaiDecision:
    allocated: tuple[Card, Card, Card]
    committed: tuple[Card, ...]
    retained: tuple[Card, ...]
    indices: tuple[int, ...]

    def unallocated_deck(self, opening: PlayerOpening, deck: Sequence[Card]) -> list[Card]:
        """Remove exactly the three offered physical slots, not equal card objects.

        The result belongs to the next Tachiai resolver. Retained cards must
        enter the initial hand separately, never reappear in the draw pile.
        """
        if opening.cards != self.allocated:
            raise ValueError("Decision belongs to a different opening.")
        return opening.remaining_deck(deck)


@dataclass
class PendingPlayerTachiai:
    opening: PlayerOpening
    _decision: TachiaiDecision | None = field(default=None, init=False, repr=False)

    @property
    def pending(self) -> bool:
        return self._decision is None

    def choose(self, indices: Sequence[int]) -> TachiaiDecision:
        """Consume exactly one validated pre-Tachiai choice.

        The indices are the *allocation slots*, not card IDs or names, so two
        physically distinct copies can be chosen independently. Disallow a
        second decision (e.g. replayed HTTP command).
        """
        if not self.pending:
            raise ValueError("The Tachiai decision has already been made.")
        committed, retained = self.opening.partition(indices)
        self._decision = TachiaiDecision(
            allocated=self.opening.cards,
            committed=committed,
            retained=retained,
            indices=tuple(sorted(indices)),
        )
        return self._decision

    @property
    def decision(self) -> TachiaiDecision | None:
        return self._decision
