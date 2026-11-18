"""B11 player draft: dynamic starting deck, three-option offers, and Kimarite cap.

A starting suite may be empty or contain inherited cards. Draft to 28,
requiring at least three and at most eight distinct Kimarite. Existing owned cards are
never offered again. Generated-only finishing moves are not draftable.
"""
from __future__ import annotations

import hashlib
from collections import Counter
import json
import random

from .catalog import (
    CARD_POOL, B9_CARD_POOL, B11_CARD_POOL, B12_CARD_POOL, PLAYER_DRAFT_CARD_POOL, card_by_name,
)

STARTERS = ("Yorikiri", "Oshidashi", "Oshi", "Tsuki",
            "Gain Left Grip", "Gain Right Grip", "Give Ground", "Sonkyo")
TARGET_SIZE = 28
MAX_KIMARITE = 8
MIN_KIMARITE = 3
GENERATED_ONLY = frozenset(("Okuridashi", "Okuritaoshi"))
_ORIGINAL_POOL = {
    card.name: card for card in (*CARD_POOL, *B9_CARD_POOL, *B11_CARD_POOL, *B12_CARD_POOL)
    if card.name not in GENERATED_ONLY
}

AVAILABLE = _ORIGINAL_POOL | {card.name: card for card in PLAYER_DRAFT_CARD_POOL}


def validate_starting_cards(starting: list[str]) -> None:
    if not isinstance(starting, list) or len(starting) > TARGET_SIZE:
        raise ValueError("Starting deck must contain 0–28 cards.")
    if any(not isinstance(name, str) or name not in AVAILABLE for name in starting):
        raise ValueError("Starting deck contains an unavailable card.")
    if any(count > 2 for count in Counter(starting).values()):
        raise ValueError("Inherited starting cards may contain at most two copies per card.")
    if sum(AVAILABLE[name].is_kimarite for name in starting) > MAX_KIMARITE:
        raise ValueError("Starting deck exceeds eight Kimarite.")


def options_for(starting: list[str], picks: list[str], seed: int, *, legacy: bool = False) -> list[str]:
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
    pool = _ORIGINAL_POOL if legacy else AVAILABLE
    remaining = [
        n for n, card in pool.items() if n not in owned
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
    # Saved drafts may have accepted an offer from before the pool expanded.
    for i, name in enumerate(picks):
        if (name not in options_for(starting, picks[:i], seed)
                and name not in options_for(starting, picks[:i], seed, legacy=True)):
            raise ValueError(f"Invalid draft choice at pick {i + 1}.")
    deck = [*starting, *picks]
    if sum(AVAILABLE[n].is_kimarite for n in deck) < MIN_KIMARITE:
        raise ValueError("Completed deck requires at least three Kimarite.")
    return deck


def grow_deck(starting: list[str], picks: list[str], draft_seed: int,
              duplicated_indices: list[int]) -> tuple[list[str], list[str]]:
    """Build a 28–40 card pool from distinct physical original positions."""
    originals = validate_draft(starting, picks, draft_seed)
    if (not isinstance(duplicated_indices, list)
            or len(duplicated_indices) > 12
            or any(type(i) is not int or not 0 <= i < 28 for i in duplicated_indices)
            or len(set(duplicated_indices)) != len(duplicated_indices)):
        raise ValueError("At most 12 distinct originals may be duplicated.")
    return (
        originals + [originals[i] for i in duplicated_indices],
        [f"original:{i}" for i in range(28)]
        + [f"duplicate:{i}" for i in duplicated_indices],
    )


def remove_from_deck(deck, ids, excluded):
    if (not isinstance(excluded, list) or len(excluded) > 4
            or any(not isinstance(card_id, str) or card_id not in ids for card_id in excluded)
            or len(set(excluded)) != len(excluded) or len(deck) - len(excluded) < 28):
        raise ValueError("Invalid interview deck exclusions.")
    return ([name for name, card_id in zip(deck, ids) if card_id not in excluded],
            [card_id for card_id in ids if card_id not in excluded])


def deal_block(deck: list[str], seed: int, ids: list[str] | None = None,
               *, guaranteed=(), previous=()) -> list[dict]:
    """Sample nine current-deck physical copies; presentation uses card_info."""
    from .b10_card_info import card_info
    if not isinstance(deck, list) or len(deck) < 9:
        raise ValueError("A block requires at least nine cards.")
    if any(name not in AVAILABLE for name in deck):
        raise ValueError("Unknown card in player deck.")
    if ids is None:
        ids = [f"original:{i}" for i in range(len(deck))]
    if len(ids) != len(deck) or len(set(ids)) != len(ids):
        raise ValueError("Invalid physical card identities.")
    rng = random.Random(seed)
    if (not isinstance(guaranteed, (list, tuple)) or len(guaranteed) > 3
            or any(not isinstance(card_id, str) or card_id not in ids for card_id in guaranteed)
            or len(set(guaranteed)) != len(guaranteed)):
        raise ValueError("Invalid guaranteed interview cards.")
    if (not isinstance(previous, (list, tuple)) or len(previous) > 9
            or any(not isinstance(card_id, str) for card_id in previous)):
        raise ValueError("Invalid prior deal for Fresh Nine.")
    forced = [ids.index(card_id) for card_id in guaranteed]
    available = [i for i in range(len(deck)) if i not in forced]
    if previous:
        rng.shuffle(available)
        available.sort(key=lambda i: ids[i] in previous)
        selected = forced + available[:9 - len(forced)]
    else:
        selected = forced + rng.sample(available, 9 - len(forced))
    if forced:
        rng.shuffle(selected)
    return [{**card_info(card_by_name(deck[j])), "deal_index": i,
             "instance_id": ids[j]} for i, j in enumerate(selected)]
