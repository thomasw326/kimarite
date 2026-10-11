"""Current V5 six-axis affinity for AI deck construction and card selection.

Source snapshot: data/card_affinity_v5.json. No runtime Google Sheets dependency.
"""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from .styles_v5 import STYLES

@lru_cache(maxsize=1)
def _ratings():
    path = Path(__file__).resolve().parents[2] / "data" / "card_affinity_v5.json"
    obj = json.loads(path.read_text(encoding="utf-8"))
    return {row["name"]: tuple(row["ratings"]) for row in obj["cards"]}

def archetype(name: str) -> str:
    if name in STYLES:
        return name
    for style in STYLES:
        if name == style + " A" or name == style + " B":
            return style
    raise KeyError(f"Unknown wrestler style: {name}")

def affinity(style: str, card_name: str) -> int:
    profile = STYLES[archetype(style)]
    ratings = _ratings().get(card_name)
    if ratings is None:
        # Unrated cards are neutral, not automatically low-priority.
        return 0
    return sum(w * (v - 3) for w, v in zip(profile.six_axis_weights, ratings))

def preferred(cards, style: str, limit: int):
    """Highest-rated *available* unique names; ties alphabetical."""
    unique = {card.name: card for card in cards}
    return sorted(unique.values(), key=lambda card: (-affinity(style, card.name), card.name))[:limit]

def least_useful(cards, style: str, count: int, protected=()):
    """Trim lowest-affinity card *instances*, never protected cards."""
    protected = set(protected)
    options = [c for c in cards if c.card_id not in protected]
    options.sort(key=lambda c: (affinity(style, c.name), c.name, c.card_id))
    return frozenset(c.card_id for c in options[:max(0, count)])
