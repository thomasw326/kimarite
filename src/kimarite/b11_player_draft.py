"""B11 player draft: dynamic starting deck, three-option offers, and Kimarite cap.

A starting suite may already include inherited cards. Draft to 28, requiring
at least three and at most eight distinct Kimarite. Existing owned cards are
never offered again. Generated-only finishing moves are not draftable.
"""
from __future__ import annotations

import hashlib
from collections import Counter
import json
import random

from .catalog import CARD_POOL, B9_CARD_POOL, card_by_name

STARTERS = ("Yorikiri", "Oshidashi", "Oshi", "Tsuki",
            "Gain Left Grip", "Gain Right Grip", "Give Ground", "Shiko Stomp")
TARGET_SIZE = 28
MAX_KIMARITE = 8
MIN_KIMARITE = 3
GENERATED_ONLY = frozenset(("Okuridashi", "Okuritaoshi"))
AVAILABLE = {
    card.name: card for card in (*CARD_POOL, *B9_CARD_POOL)
    if card.name not in GENERATED_ONLY
}


def validate_starting_cards(starting: list[str]) -> None:
    if not isinstance(starting, list) or not 3 <= len(starting) <= TARGET_SIZE:
        raise ValueError("Starting deck must contain 3–28 cards.")
    if any(not isinstance(name, str) or name not in AVAILABLE for name in starting):
        raise ValueError("Starting deck contains an unavailable card.")
    if max(Counter(starting).values()) > 2:
        raise ValueError("Inherited starting cards may contain at most two copies per card.")
    if sum(AVAILABLE[name].is_kimarite for name in starting) > MAX_KIMARITE:
        raise ValueError("Starting deck exceeds eight Kimarite.")


def options_for(starting: list[str], picks: list[str], seed: int) -> list[str]:
    """A reproducible three-card choice, conditional on the CURRENT deck."""
    validate_starting_cards(starting)
    if not isinstance(picks, list) or any(not isinstance(n, str) for n in picks):
        raise ValueError("Draft selections must be card names.")
    owned = [*starting, *picks]
    if len(owned) >= TARGET_SIZE:
        return []
    if (len(set(picks)) != len(picks) or set(picks) & set(starting)
            or any(n not in AVAILABLE for n in owned)):
        raise ValueError("Draft contains unavailable or repeated cards.")
    kimarite = sum(AVAILABLE[n].is_kimarite for n in owned)
    if kimarite > MAX_KIMARITE:
        raise ValueError("Draft exceeds eight Kimarite.")
    # Below three Kimarite, force a three-Kimarite offer before mixed picks.
    only_kimarite = kimarite < MIN_KIMARITE
    remaining = [
        n for n, card in AVAILABLE.items() if n not in owned
        and (card.is_kimarite if only_kimarite else
             (not card.is_kimarite if kimarite == MAX_KIMARITE else True))
    ]
    if len(remaining) < 3:
        raise ValueError("Not enough eligible cards for a three-card draft offer.")
    signature = json.dumps([int(seed), starting, picks], separators=(",", ":"))
    rng = random.Random(int.from_bytes(hashlib.sha256(signature.encode()).digest()[:8], "big"))
    return rng.sample(sorted(remaining), 3)


def validate_draft(starting: list[str], picks: list[str], seed: int) -> list[str]:
    validate_starting_cards(starting)
    if not isinstance(picks, list) or len(starting) + len(picks) != TARGET_SIZE:
        raise ValueError("Draft must finish at exactly 28 cards.")
    for i, name in enumerate(picks):
        if name not in options_for(starting, picks[:i], seed):
            raise ValueError(f"Invalid draft choice at pick {i + 1}.")
    deck = [*starting, *picks]
    if sum(AVAILABLE[n].is_kimarite for n in deck) < MIN_KIMARITE:
        raise ValueError("Completed deck requires at least three Kimarite.")
    return deck


def deal_block(deck: list[str], seed: int) -> list[dict]:
    """Sample nine current-deck physical copies; presentation uses card_info."""
    from .b10_card_info import card_info
    if not isinstance(deck, list) or len(deck) < 9:
        raise ValueError("A block requires at least nine cards.")
    if any(name not in AVAILABLE for name in deck):
        raise ValueError("Unknown card in player deck.")
    rng = random.Random(seed)
    selected = rng.sample(deck, 9)
    return [{**card_info(card_by_name(n)), "deal_index": i} for i, n in enumerate(selected)]
