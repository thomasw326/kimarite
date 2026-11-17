"""Seeded six-basho roster allocation for the B12 42-place top division.

This module is deliberately independent of bout scheduling and the browser UI.
A fresh campaign gets one of *every* existing B12 framework, without replacement;
the assignment is then persisted rather than reshuffled during tournaments.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import random

from .styles_v5 import STYLES

DATA = Path(__file__).resolve().parents[2] / "data"
FORMATS = DATA / "b12_60_framework_decks.json"
SHIKONA = DATA / "b12_fictional_shikona.json"
AI_COUNT = 60
ACTIVE_AI = 41
RESERVE_AI = 19
PLAYER_RANK = 42
BASHO_COUNT = 6


def load_formats() -> list[dict]:
    """Read the source-verified 15-by-four framework register unchanged."""
    document = json.loads(FORMATS.read_text(encoding="utf-8"))
    formats = document["frameworks"]
    ids = [f["id"] for f in formats]
    if len(formats) != AI_COUNT or set(ids) != {f"{i:02d}" for i in range(1, AI_COUNT + 1)}:
        raise ValueError("B12 requires exactly 60 unique, numbered format IDs")
    styles = Counter(f["style_proxy"] for f in formats)
    if len(STYLES) != 15 or styles != Counter({style: 4 for style in STYLES}):
        raise ValueError("B12 requires exactly four formats for each of the 15 AI styles")
    for f in formats:
        if not isinstance(f.get("identity"), str) or not f["identity"].strip():
            raise ValueError(f"Missing B12 format description: {f['id']}")
        if len(f["base"]) != 28 or len(f["duplicates"]) != 12:
            raise ValueError(f"B12 28+12 source format is incomplete: {f['id']}")
    return formats


def load_shikona() -> list[str]:
    """Reuse the project-approved fictional-name pool rather than real wrestler names."""
    names = json.loads(SHIKONA.read_text(encoding="utf-8"))["names"]
    if len(names) < AI_COUNT or any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError("Need at least 60 nonblank fictional shikona")
    if len({name.casefold() for name in names}) != len(names):
        raise ValueError("Fictional shikona must be unique, ignoring case")
    return names


def make_roster(seed: int, player_name: str) -> dict:
    """Create 41 ranked AI, the player at #42, and 19 ordered unused reserves.

    All 60 format IDs are permuted once without replacement. Shuffling names
    and ranking slots at this boundary makes it possible for any given format
    to remain in the reserve queue for an entire six-basho campaign.
    """
    if type(seed) is not int:
        raise TypeError("Roster seed must be an integer")
    if not isinstance(player_name, str) or not player_name.strip():
        raise ValueError("Player must have a nonempty wrestler name")
    player_name = player_name.strip()
    formats = load_formats()
    name_pool = [n for n in load_shikona() if n.casefold() != player_name.casefold()]
    if len(name_pool) < AI_COUNT:
        raise ValueError("Name pool lacks 60 names after excluding the player's name")
    rng = random.Random(seed)
    rng.shuffle(formats)
    rng.shuffle(name_pool)
    wrestlers = []
    for i, (fmt, name) in enumerate(zip(formats, name_pool)):
        active = i < ACTIVE_AI
        wrestlers.append({
            "wrestler_id": f"ai-{i + 1:02d}",
            "name": name,
            "format_id": fmt["id"],
            "ai_style": fmt["style_proxy"],
            "format_description": fmt["identity"],  # Optional testing detail.
            "division": "top" if active else "reserve",
            "rank": i + 1 if active else None,
        })
    roster = {
        "schema": "b12-division-roster-v1",
        "seed": seed,
        "player": {"name": player_name, "rank": PLAYER_RANK},
        "wrestlers": wrestlers,
        "reserve_queue": [w["wrestler_id"] for w in wrestlers[ACTIVE_AI:]],
    }
    validate_roster(roster)
    return roster


def validate_roster(roster: dict) -> None:
    """Fail closed on duplicate format/name IDs or a broken 41+19 split."""
    rows = roster["wrestlers"]
    formats = load_formats()
    expected_ids = {fmt["id"] for fmt in formats}
    if len(rows) != AI_COUNT:
        raise ValueError("Roster must contain exactly 60 AI wrestlers")
    if len({w["wrestler_id"] for w in rows}) != AI_COUNT:
        raise ValueError("Duplicate wrestler IDs")
    if {w["format_id"] for w in rows} != expected_ids or len({w["format_id"] for w in rows}) != AI_COUNT:
        raise ValueError("Every B12 format must be assigned once, without duplication")
    if len({w["name"].casefold() for w in rows}) != AI_COUNT:
        raise ValueError("Duplicate wrestler display names")
    if roster["player"]["name"].casefold() in {w["name"].casefold() for w in rows}:
        raise ValueError("Player name collides with AI display name")
    if Counter(w["ai_style"] for w in rows) != Counter({s: 4 for s in STYLES}):
        raise ValueError("Roster must retain all fifteen AI styles, four formats each")
    by_format = {f["id"]: f for f in formats}
    for w in rows:
        f = by_format[w["format_id"]]
        if w["ai_style"] != f["style_proxy"] or w["format_description"] != f["identity"]:
            raise ValueError("A wrestler's style/description does not match its format")
    active, reserves = rows[:ACTIVE_AI], rows[ACTIVE_AI:]
    if [w["rank"] for w in active] != list(range(1, PLAYER_RANK)):
        raise ValueError("Top division AI ranks must be 1 through 41")
    if any(w["division"] != "top" for w in active):
        raise ValueError("Top division AI must be active")
    if any(w["rank"] is not None or w["division"] != "reserve" for w in reserves):
        raise ValueError("Reserve AI cannot already occupy a top-division rank")
    if roster["player"]["rank"] != PLAYER_RANK:
        raise ValueError("Created player must enter at rank 42")
    if roster["reserve_queue"] != [w["wrestler_id"] for w in reserves]:
        raise ValueError("Reserve queue must contain the original 19 hidden wrestlers in order")
