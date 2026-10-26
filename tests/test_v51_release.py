"""V5.1 release contract: pool, styles, difficulty, and selected finishers.

These tests are intentionally independent of obsolete 16-Kimarite V5 audit expectations.
"""
import json
import random
from pathlib import Path

from kimarite.catalog import CARD_POOL, STARTING_KIMARITE
from kimarite.kimarite import KIMARITE_PREDICATES
from kimarite.affinity_v5 import affinity
from kimarite.styles_v5 import STYLES
from kimarite.style_builds_v5 import build_style


LIVE_ORB_OVERRIDES = {"Read the Move": (0, 1, 1)}  # Live approved print supersedes V5.1 manifest.

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "data" / "card_pool_v5_1.json").read_text(encoding="utf-8"))


def test_release_pool_exactly_matches_manifest():
    assert MANIFEST["version"].startswith("5.1")
    assert len(STYLES) == 15
    assert len(CARD_POOL) == 61
    assert sum(not card.is_kimarite for card in CARD_POOL) == 39
    assert sum(card.is_kimarite for card in CARD_POOL) == 22
    expected_names = {entry["name"] for entry in MANIFEST["cards"]}
    assert {card.name for card in CARD_POOL} == expected_names
    selected = {card.name for card in CARD_POOL if card.is_kimarite}
    assert selected == {card.name for card in STARTING_KIMARITE}
    assert selected == set(KIMARITE_PREDICATES)


def test_release_catalog_orbs():
    for row in MANIFEST["cards"]:
        card = next(card for card in CARD_POOL if card.name == row["name"])
        if row["type"] == "Non-Kimarite":
            expected = tuple(row["orbs"][key] for key in ("power", "technique", "spirit"))
        else:
            expected = (row["orbs"].count("🟣"), row["orbs"].count("🟢"), row["orbs"].count("🟠"))
        assert (card.power, card.technique, card.spirit) == LIVE_ORB_OVERRIDES.get(row["name"], expected), row["name"]


def test_fifteen_styles_prune_seven_at_baseline_and_restore_at_negative_difficulty():
    for name in STYLES:
        easier = build_style(name, seed=91, difficulty=-7)
        baseline = build_style(name, seed=91, difficulty=0)
        harder = build_style(name, seed=91, difficulty=7)
        assert len(easier.excluded_ids) == 0
        assert len(baseline.excluded_ids) == 7
        assert len(harder.excluded_ids) == 14
        assert baseline.excluded_ids.issubset(harder.excluded_ids)


def test_optional_stat_boosts_off_by_default():
    for name, profile in STYLES.items():
        base = build_style(name, seed=7, difficulty=7)
        assert (base.fighter.wrestler.base_power,
                base.fighter.wrestler.base_technique,
                base.fighter.wrestler.base_spirit) == profile.stats
        boosted = build_style(name, seed=7, difficulty=7, enable_stat_boosts=True)
        assert tuple(x + 1 for x in profile.stats) == (
            boosted.fighter.wrestler.base_power,
            boosted.fighter.wrestler.base_technique,
            boosted.fighter.wrestler.base_spirit,
        )


def test_affinity_still_scores_catalog_alias():
    assert affinity("Speed Demon", "Explosive Step — Fumikomi") == affinity("Speed Demon", "Explosive Step")


def test_fifteen_style_round_robin_has_105_unique_matchups():
    from scripts.styles_test import round_robin_pairs
    pairs = round_robin_pairs(15, 20261010)
    assert len(pairs) == 105
    assert len({frozenset(pair) for pair in pairs}) == 105
    assert {i for a, b in pairs for i in (a, b)} == set(range(15))
