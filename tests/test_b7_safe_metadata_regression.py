"""B7 catalog invariants: documentation cleanup must not alter runtime balance."""
import json
from pathlib import Path

from kimarite import affinity_v5
from kimarite.r21_gauntlet import load_arms
from kimarite.r21_variant_rules import build_variant_card


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
    assert len(names) == 61
    assert len(set(names)) == 61
    assert "61 cards" in data["b7_coverage_note"]
    assert "61" in data["b7_coverage_note"]
    assert all(len(row["ratings"]) == 6 for row in data["cards"])
    assert affinity_v5.affinity("The Technician", "__unknown_b7_card__") == 0


