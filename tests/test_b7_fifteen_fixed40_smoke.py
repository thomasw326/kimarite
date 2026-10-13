"""Smoke the entire B7 15-style matchup grid without launching the big batch."""
from pathlib import Path
import sys


def test_fifteen_fixed40_all_matchups(tmp_path):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        import b7_fifteen_fixed40_roundrobin as tournament
        assert len(tournament.NAMES) == 15
        assert len(tournament.PAIRS) == 120
        decks = tournament.snapshot()
        assert len(decks) == 15
        assert all(sum(deck.values()) == 40 for deck in decks.values())
        assert decks["Mawashi Specialist"]["Shitatenage"] == 2
        assert decks["Speed Demon"]["Oshidashi"] == 2
        tournament.run(0, 1, tmp_path)
        import json
        manifest = json.loads((tmp_path / "manifest.json").read_text())
        assert manifest["bouts"] == 240
        assert manifest["incomplete"] == 0
    finally:
        sys.path.remove(str(scripts))
