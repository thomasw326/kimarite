"""Deterministic Draw Pile search primitives used by R21 experimental cards.

The top of the Draw Pile is index 0. Search is NOT scrying: it cannot
select a lower card, does not reveal or move nonmatching cards, and never
shuffles, sorts, rotates, or bottoms the pile.
"""
from __future__ import annotations

from collections.abc import Callable

from .models import Card, FighterState

# Matches the names currently credited with successful Reversal in
# temporary.py under the isolated R20 battle rules. Keep in sync when the
# game's explicit Reversal classification changes.
REVERSAL_CARD_NAMES = frozenset({
    "Henka", "Pull", "Sidestep", "Immovable", "Kannuki",
})


def search_draw_pile_first(
    fighter: FighterState,
    is_match: Callable[[Card], bool],
) -> Card | None:
    """Move the topmost matching card directly from Draw Pile into hand.

    Other cards keep their identities and their existing order. Searching an
    empty deck or a deck without a match changes nothing. The match is
    automatically chosen; neither a player nor an AI provides an index.
    """
    for index, card in enumerate(fighter.draw_pile):
        if is_match(card):
            found = fighter.draw_pile.pop(index)
            fighter.hand.append(found)
            return found
    return None


def search_for_reversal(fighter: FighterState) -> Card | None:
    """Find the first card credited as Reversal in current R20 battle rules."""
    return search_draw_pile_first(
        fighter,
        lambda card: card.name in REVERSAL_CARD_NAMES,
    )
