"""Validation and ownership model for B11 player-controlled Tachiai.

This module deliberately has no game-state side effects: opening card
selection must be validated before the bout creates/consumes any cards.
The live session engine will use this boundary when its pre-Tachiai phase
is introduced.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from .models import Card


@dataclass(frozen=True)
class PlayerOpening:
    """The three cards allocated to a bout, in their original slot order."""

    cards: tuple[Card, Card, Card]

    @classmethod
    def from_names(cls, deck: Sequence[Card], names: Sequence[str]) -> "PlayerOpening":
        if len(names) != 3 or any(not isinstance(name, str) for name in names):
            raise ValueError("A player-controlled opening requires exactly three cards.")
        available = Counter(card.name for card in deck)
        requested = Counter(names)
        if any(number > available[name] for name, number in requested.items()):
            raise ValueError("Opening selection exceeds the copies in this deck.")
        remaining = list(deck)
        picked = []
        for name in names:
            index = next(i for i, card in enumerate(remaining) if card.name == name)
            picked.append(remaining.pop(index))
        return cls(tuple(picked))

    def partition(self, committed_indices: Sequence[int]) -> tuple[tuple[Card, ...], tuple[Card, ...]]:
        """Return (Tachiai commits, opening hand) in allocated order.

        Index-based selection distinguishes legitimate duplicate card names.
        Zero to three committed cards are all legal.
        """
        if (
            not isinstance(committed_indices, (list, tuple))
            or any(type(index) is not int or index not in (0, 1, 2) for index in committed_indices)
            or len(set(committed_indices)) != len(committed_indices)
        ):
            raise ValueError("Commit indices must be distinct integers from 0 to 2.")
        chosen = set(committed_indices)
        committed = tuple(card for i, card in enumerate(self.cards) if i in chosen)
        retained = tuple(card for i, card in enumerate(self.cards) if i not in chosen)
        return committed, retained

    def remaining_deck(self, deck: Sequence[Card]) -> list[Card]:
        """Remove one exact instance per allocated card, preserving deck order."""
        remaining = list(deck)
        for card in self.cards:
            for i, existing in enumerate(remaining):
                if existing is card:
                    remaining.pop(i)
                    break
            else:
                raise ValueError("An allocated card is not present in this deck.")
        return remaining
