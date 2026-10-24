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


def test_opening_is_visible_without_revealing_opponent_draw():
    from kimarite.b10_human_session import public_snapshot, new_b10_session
    bout=new_b10_session("Arm Controller", "Speed Demon", seed=101)
    state=public_snapshot(bout)
    assert state["opening"]["human"]["starting_kimarite"]["is_kimarite"]
    assert len(state["opening"]["human"]["tachiai_orbs"])==3
    assert "top_of_deck" not in state["opening"]["opponent"]
    assert any("Tachiai orbs" in e for e in state["events"])

def test_explicit_human_opening_preserves_40_card_pool_and_ai_autoselection():
    from kimarite.b10_human_session import opening_options, new_b10_session
    from kimarite.models import Side
    names=opening_options("Arm Controller")
    chosen={"kimarite":names["kimarite"][0]["name"],"prepared":names["ordinary"][0]["name"],"top":names["ordinary"][1]["name"]}
    bout=new_b10_session("Arm Controller","The Technician",seed=42,opening=chosen)
    own=bout.state.fighter(Side.A).wrestler
    assert own.starting_kimarite.name==chosen["kimarite"]
    assert own.prepared_tachiai_card.name==chosen["prepared"]
    assert own.top_of_deck_card.name==chosen["top"]
    with pytest.raises(ValueError):
        new_b10_session("Arm Controller","The Technician",seed=42,opening={"kimarite":chosen["kimarite"],"prepared":chosen["prepared"],"top":"not a card"})


def test_morozashi_with_both_grips_is_playable_and_has_delayed_push():
    from kimarite.catalog import card_by_name
    from kimarite.models import Side, GripState
    session = new_b10_session("Arm Controller", "The Technician", seed=42)
    own = session.state.fighter(Side.A)
    session.state.active_side = Side.A
    session.state.winner = None
    session.stopped_reason = None
    session.awaiting_human = True
    session.pending_selection = None
    own.plays_remaining = 2
    session.state.fighter(Side.B).temporary_zone.clear()
    own.left_grip = GripState.GRIP
    own.right_grip = GripState.GRIP
    own.hand.append(card_by_name("Morozashi"))
    idx = len(own.hand) - 1
    assert idx in [action.hand_index for action in session.actions()]
    assert public_snapshot(session)["human"]["hand"][idx]["unavailable_reason"] is None
    session.play(idx)
    assert any(t.card.name == "Morozashi" for t in own.temporary_zone) or any(t.card.name == "Morozashi" for t in session.state.fighter(Side.A).temporary_zone)


def test_every_approved_opponent_maps_to_registered_v5_style():
    from kimarite.b10_human_session import STYLE_PROXIES
    from kimarite.styles_v5 import STYLES
    assert all(STYLE_PROXIES.get(name, name) in STYLES for name in roster())


def test_outside_fighter_can_complete_opponent_turn_after_human_plays():
    from kimarite.models import Side
    session = new_b10_session(
        "Hand-Size Specialist", "Outside Fighter", seed=20261021,
        opening={"kimarite": "Katasukashi",
                 "prepared": "Attempt Two-Handed Grip",
                 "top": "Attempt Deep Outside Grip"},
    )
    if session.pending_selection:
        session.choose_cards(list(range(session.pending_selection.keep)))
    assert session.awaiting_human
    session.end_turn()
    assert session.stopped_reason is None or "Unknown V5 style" not in session.stopped_reason
    assert any(side is Side.B for side, name in session.state.card_plays) or session.finished or session.awaiting_human


def test_public_discard_piles_are_inspectable_without_hidden_decks():
    from kimarite.catalog import card_by_name
    from kimarite.models import Side
    session = new_b10_session("Arm Controller", "The Technician", seed=42)
    session.state.fighter(Side.A).discard_pile.append(card_by_name("Yori"))
    session.state.fighter(Side.B).discard_pile.append(card_by_name("Shove"))
    snapshot = public_snapshot(session)
    assert snapshot["human"]["discard"][-1]["name"] == "Yori"
    assert snapshot["opponent"]["discard"][-1]["name"] == "Shove"
    assert snapshot["human"]["discard"][-1]["description_status"] == "verified"
    assert "hand" not in snapshot["opponent"]
    assert "draw_pile" not in snapshot["opponent"]



def test_management_deal_uses_actual_deck_copies_and_is_reproducible():
    from collections import Counter
    from kimarite.b10_human_session import management_deal, ROSTER_PATH
    import json
    name = "Heavy Hitter"
    a = management_deal(name, 123)
    b = management_deal(name, 123)
    assert a == b
    assert len(a["cards"]) == 9
    assert sum(c["is_kimarite"] for c in a["cards"]) == 3
    assert len({c["deal_index"] for c in a["cards"]}) == 9
    dealt = Counter(c["name"] for c in a["cards"])
    source = Counter(json.loads(ROSTER_PATH.read_text())["decks"][name]["cards"])
    assert all(n <= source[k] for k, n in dealt.items())
    for c in a["cards"]:
        assert c["description_status"] == "verified"


def test_management_three_openings_accepted_by_b10_controller():
    from kimarite.b10_human_session import management_deal, new_b10_session
    d = management_deal("Heavy Hitter", 251)
    groups = [c for c in d["cards"] if c["is_kimarite"]]
    ordinary = [c for c in d["cards"] if not c["is_kimarite"]]
    for index in range(3):
        opening = {"kimarite": groups[index]["name"],
                   "prepared": ordinary[index*2]["name"],
                   "top": ordinary[index*2+1]["name"]}
        bout = new_b10_session("Heavy Hitter", "Bulldozer",
                               seed=252+index, opening=opening)
        assert bout.state.fighter(bout.human_side).wrestler.starting_kimarite.name == opening["kimarite"]
