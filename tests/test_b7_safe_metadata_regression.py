"""B7 catalog invariants: documentation cleanup must not alter runtime balance."""
import json
from pathlib import Path

from kimarite import affinity_v5
from kimarite.r21_gauntlet import load_arms
from kimarite.r21_variant_rules import build_variant_card
from kimarite.r26_style_final22 import install_final22


ROOT = Path(__file__).resolve().parents[1]


def test_selected_b7_metadata_matches_runtime_overrides():
    arms = {arm.arm_id: arm for arm in load_arms()}
    assert arms["R21-R22-ABI-1"].win_text == "Total usable Grip ≥2 · Power ≥10 · Momentum ≥1"
    kot = arms["R21-KOT-R1"]
    assert kot.win_text == "Opponent has no usable Grip · Momentum ≥3 · Own hand ≥6"
    assert (build_variant_card(kot.arm_id, card_id=900).power,
            build_variant_card(kot.arm_id, card_id=900).technique,
            build_variant_card(kot.arm_id, card_id=900).spirit) == (1, 2, 0)


def test_b7_affinity_coverage_explicit_and_unrated_neutral():
    data = json.loads((ROOT / "data/card_affinity_v5.json").read_text(encoding="utf-8"))
    names = [row["name"] for row in data["cards"]]
    assert len(names) == 59
    assert len(set(names)) == 59
    assert "61 cards" in data["b7_coverage_note"]
    assert "neutral" in data["b7_coverage_note"]
    assert all(len(row["ratings"]) == 6 for row in data["cards"])
    assert affinity_v5.affinity("The Technician", "__unknown_b7_card__") == 0


def test_b7_install_keeps_22_selected_kimarite_and_kotenage_orbs():
    from kimarite import style_builds_v5
    install_final22()
    pool = style_builds_v5.CARD_POOL
    winners = [card for card in pool if card.is_kimarite]
    assert len({card.name for card in winners}) == 22
    kot = next(card for card in winners if card.name == "R21:R21-KOT-R1")
    assert (kot.power, kot.technique, kot.spirit) == (1, 2, 0)
