"""Per-wrestler card-slot cohorts remain attributed to the correct style."""
from kimarite import style_round_robin_v5 as report


def test_style_card_slot_report_groups_and_lift(monkeypatch):
    monkeypatch.setattr(
        report, "STYLES",
        {name: report.STYLES[name] for name in ("Heavy Hitter", "Bulldozer")},
    )
    result = report.run_round_robin(repetitions=1)
    assert result["planned_bouts"] == 2
    assert set(result["style_card_slot_outcomes"]) == {"Heavy Hitter", "Bulldozer"}
    for style in ("Heavy Hitter", "Bulldozer"):
        slots = result["style_card_slot_outcomes"][style]
        for role in ("Starting Kimarite", "Tachiai", "Top"):
            assert sum(row["appearances"] for row in slots[role].values()) == 2
        for role, cards in slots.items():
            for card in cards.values():
                assert card["wins"] + card["losses"] <= card["appearances"]
        assert "Opening Hand" in slots
        assert "Opening Hand" in result["style_card_placement_lift"][style]
        lifted = result["style_card_placement_lift"][style]
        for role in ("Starting Kimarite", "Tachiai", "Top"):
            assert set(lifted[role]) == set(slots[role])
            for card in lifted[role].values():
                if card["win_rate"] is not None:
                    assert -100 <= card["lift_vs_style_pp"] <= 100
    for role in ("Starting Kimarite", "Tachiai", "Top"):
        per_style = sum(
            card["appearances"] for slots in result["style_card_slot_outcomes"].values()
            for card in slots[role].values()
        )
        overall = sum(card["appearances"] for card in result["card_slot_outcomes"][role].values())
        assert per_style == overall
