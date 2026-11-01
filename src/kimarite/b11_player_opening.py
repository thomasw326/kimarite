"""Validate three allocated player cards by physical deck slot, not Card identity.

The catalogue returns shared immutable Card objects: separate deck copies may
be the *same* Python object. Slot indices, rather than object identity, are
the authority for ownership and duplicate counts.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from typing import Sequence
from .models import Card


@dataclass(frozen=True)
class PlayerOpening:
    cards: tuple[Card, Card, Card]
    deck_indices: tuple[int, int, int]

    @classmethod
    def from_names(cls, deck: Sequence[Card], names: Sequence[str]) -> "PlayerOpening":
        if len(names) != 3 or any(not isinstance(name, str) for name in names):
            raise ValueError("A player-controlled opening requires exactly three cards.")
        available = Counter(card.name for card in deck)
        requested = Counter(names)
        if any(number > available[name] for name, number in requested.items()):
            raise ValueError("Opening selection exceeds the copies in this deck.")
        used: set[int] = set()
        positions: list[int] = []
        for name in names:
            position = next(i for i, card in enumerate(deck)
                            if i not in used and card.name == name)
            used.add(position)
            positions.append(position)
        return cls(tuple(deck[i] for i in positions), tuple(positions))

    def partition(self, committed_indices: Sequence[int]) -> tuple[tuple[Card, ...], tuple[Card, ...]]:
        if (not isinstance(committed_indices, (list, tuple))
                or any(type(i) is not int or i not in (0, 1, 2) for i in committed_indices)
                or len(set(committed_indices)) != len(committed_indices)):
            raise ValueError("Commit indices must be distinct integers from 0 to 2.")
        selected = set(committed_indices)
        return (tuple(c for i, c in enumerate(self.cards) if i in selected),
                tuple(c for i, c in enumerate(self.cards) if i not in selected))

    def remaining_deck(self, deck: Sequence[Card]) -> list[Card]:
        if any(i >= len(deck) or deck[i].name != card.name
               for i, card in zip(self.deck_indices, self.cards)):
            raise ValueError("The allocated cards no longer match the deck.")
        return [card for i, card in enumerate(deck) if i not in self.deck_indices]
