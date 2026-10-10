"""Compare current simulator cards against the frozen Card Library source.

Only published orb fields and active/retired presence are asserted here.
Text effects require separate behavior-by-behavior parity tests.
"""
import json
from pathlib import Path

from kimarite.catalog import CARD_POOL, STARTING_KIMARITE


SOURCE = json.loads((Path(__file__).resolve().parents[1] / "data" / "v5_print_pool_snapshot.json").read_text())
ALIASES = {"Explosive Step": "Explosive Step — Fumikomi"}
# Approved overrides take precedence over the immutable historical snapshot.
APPROVED_ORB_OVERRIDES = {"Get Underneath": (1, 1, 0), "Shiko Stomp": (1, 1, 1), "Stare Down": (1, 1, 1)}


def test_current_print_pool_orbs_match_snapshot():
    live = {
        name: (card.power, card.technique, card.spirit)
        for card in (*CARD_POOL, *STARTING_KIMARITE)
        for name in (card.name,)
    }
    for row in SOURCE["cards"]:
        if row["copy"] is None or row["copy"] <= 0:
            continue
        if row["name"].startswith("Chosen Kimarite") or row["name"] == "Injury":
            continue
        name = ALIASES.get(row["name"], row["name"])
        assert name in live, f"Missing {name}, row {row['sheet_row']}"
        assert live[name] == APPROVED_ORB_OVERRIDES.get(name, (row["power"], row["technique"], row["spirit"])), name


def test_retired_cards_absent_from_pool():
    names = {card.name for card in CARD_POOL}
    assert "Bad Oshi" not in names
    assert "Big Tsuki" not in names
    assert "Oshi" in names
