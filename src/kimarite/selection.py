from __future__ import annotations

from collections.abc import Iterable

from .models import Card, FighterState, Wrestler


def ai_rank_cards(cards: Iterable[Card], wrestler: Wrestler) -> list[Card]:
    """Rank looked-at cards by Primary, Secondary, then earlier reveal order."""
    indexed = list(enumerate(cards))
    indexed.sort(
        key=lambda item: (
            -item[1].orbs(wrestler.primary),
            -item[1].orbs(wrestler.secondary),
            item[0],
        )
    )
    return [card for _, card in indexed]


def ai_choose_from_look(cards: list[Card], wrestler: Wrestler, keep: int) -> list[Card]:
    if keep < 0 or keep > len(cards):
        raise ValueError("keep must be between 0 and number of looked-at cards")
    return ai_rank_cards(cards, wrestler)[:keep]


def look_from_top(fighter: FighterState, count: int) -> list[Card]:
    if count < 0:
        raise ValueError("count must be non-negative")
    return list(fighter.draw_pile[:count])


def keep_and_bottom(
    fighter: FighterState,
    looked: list[Card],
    kept: list[Card],
) -> None:
    if len(looked) > len(fighter.draw_pile):
        raise ValueError("looked cards exceed draw pile")
    if fighter.draw_pile[: len(looked)] != looked:
        raise ValueError("looked cards must be the current top of the draw pile")

    remaining = list(looked)
    for card in kept:
        try:
            remaining.remove(card)
        except ValueError as exc:
            raise ValueError("kept card was not in looked cards") from exc

    fighter.draw_pile = fighter.draw_pile[len(looked) :]
    fighter.hand.extend(kept)
    fighter.draw_pile.extend(remaining)


def ai_look_keep(fighter: FighterState, look: int, keep: int) -> list[Card]:
    looked = look_from_top(fighter, look)
    if len(looked) < keep:
        raise ValueError("not enough cards in draw pile to keep requested amount")
    kept = ai_choose_from_look(looked, fighter.wrestler, keep)
    keep_and_bottom(fighter, looked, kept)
    return kept
