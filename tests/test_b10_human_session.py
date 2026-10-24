"""UI session contract: existing rules and State-3 AI remain authoritative."""
import json
import pytest
from kimarite.b10_human_session import roster, new_b10_session, public_snapshot, dispatch


def test_approved_26_roster():
    names = roster()
    assert len(names) == 26 and "Arm Controller" in names
    assert not {"Attrition Fighter", "Disruptor", "Gripless Fighter", "Stability Master"} & set(names)


def test_ui_session_and_hidden_information():
    session = new_b10_session("Arm Controller", "The Technician", seed=42)
    view = public_snapshot(session)
    json.dumps(view)
    assert view["human"]["name"] == "Arm Controller"
    assert view["opponent"]["name"] == "The Technician"
    assert "hand" not in view["opponent"]
    assert "draw_pile" not in view["opponent"]
    assert "draw_pile" not in view["human"]
    assert "legal_plays" in view
    assert len(session.state.fighter_a.kimarite_zone) >= 1


def test_human_choices_are_commands_not_terminal_prompts():
    session = new_b10_session("The Technician", "Mountain", seed=91, max_turns=5)
    view = public_snapshot(session)
    if view["phase"] == "select_cards":
        keep = view["selection"]["keep"]
        view = dispatch(session, {"type":"choose_cards","indices":list(range(keep))})
    if view["phase"] == "human_turn":
        view = dispatch(session, {"type":"end_turn"})
    assert view["phase"] in {"finished", "select_cards", "human_turn"}
    json.dumps(view)


def test_unknown_wrestler_rejected():
    with pytest.raises(ValueError):
        new_b10_session("Attrition Fighter", "Mountain")
