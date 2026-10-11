"""Smoke tests for the targeted V5 Kimarite audit."""
from kimarite.kimarite_audit_v5 import audit


def test_kimarite_audit_reports_denominators_and_triggers():
    report = audit(repetitions=1, max_turns=30)
    assert report["planned_bouts"] == 210
    assert report["completed"] + sum(report["incomplete"].values()) == 210
    assert len(report["kimarite"]) == 22
    for row in report["kimarite"]:
        assert row["featured_wins"] <= row["featured"]
        assert row["starting_wins"] <= row["starting"]
        assert row["starting_trigger_wins"] <= row["trigger_wins"]
        assert row["starting_trigger_wins"] <= row["starting_wins"]
        assert row["trigger_wins"] <= row["featured_wins"]
