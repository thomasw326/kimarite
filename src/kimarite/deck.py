from __future__ import annotations

from math import floor, sin

from .catalog import CARD_POOL, card_by_name
from .models import Card, Wrestler


def sheet_seed_key(card_id: int, seed: int) -> float:
    """Match the deterministic key used by the AI-vs-AI Google Sheet."""
    raw = sin((card_id + seed) * 78.233) * 43758.5453
    return raw - floor(raw)


def build_seeded_deck(
    wrestler: Wrestler,
    seed: int,
    excluded_ids: set[int] | None = None,
) -> list[Card]:
    """Build a reproducible deck matching the current AI-vs-AI sheet structure.

    The designated Top of Deck card is first. The starting Kimarite,
    prepared Tachiai card, and designated Top of Deck card are excluded from
    the shuffled remainder by name, matching the sheet formulas.
    """
    excluded_ids = excluded_ids or set()
    reserved_names = {
        wrestler.starting_kimarite.name,
        wrestler.prepared_tachiai_card.name,
        wrestler.top_of_deck_card.name,
    }

    remainder = [
        card
        for card in CARD_POOL
        if card.card_id <= 45 and card.name not in reserved_names and card.card_id not in excluded_ids
    ]
    remainder.sort(key=lambda card: sheet_seed_key(card.card_id, seed))

    return [card_by_name(wrestler.top_of_deck_card.name), *remainder]
