"""B11 web-facing integration for approved Shitate finishers.

The rendered card glossary, draft options and live win breakdown must stay
aligned with the engine, rather than only the V5 terminal inspector.
"""
from types import SimpleNamespace

from kimarite.b10_card_info import GLOSSARY, card_info
from kimarite.b10_web import labelled_choices
from kimarite.b11_player_draft import AVAILABLE, options_for
from kimarite.b11_victory_checks import victory_checks
from kimarite.catalog import card_by_name
from kimarite.effects import ChoiceRequired
from kimarite.kimarite import kimarite_is_satisfied
from kimarite.models import BoutState, Card, FighterState, GripState, Side, Wrestler


def _state():
    blank = Card(99991, "Blank")
    a = Wrestler("A", 0, 0, 0, blank, blank, blank)
    b = Wrestler("B", 0, 0, 0, blank, blank, blank)
    return BoutState(FighterState(a, right_grip=GripState.DEEP),
                     FighterState(b))


def test_shitate_finishers_are_draftable_and_have_live_verified_card_text():
    for name in ("Shitatehineri", "Shitatedashinage"):
        assert name in AVAILABLE
        c = card_by_name(name)
        assert AVAILABLE[name] == c
        info = card_info(c)
        assert info["is_kimarite"]
        assert info["description_status"] == "verified"
        assert "Deep Right Grip" in info["description"] or "Right Grip is Deep" in info["description"]
    assert "Exhaust" in GLOSSARY
    assert "Recover" in GLOSSARY


def test_shitate_win_checks_agree_with_live_engine():
    state = _state()
    for name in ("Shitatehineri", "Shitatedashinage"):
        finish = card_by_name(name)
        actual = all(row["met"] for row in victory_checks(state, Side.A, name))
        assert actual == kimarite_is_satisfied(state, Side.A, finish)
    state.fighter_b.unstable = True
    assert all(x["met"] for x in victory_checks(state, Side.A, "Shitatedashinage"))
    assert kimarite_is_satisfied(state, Side.A, card_by_name("Shitatedashinage"))
    state.fighter_b.unstable = False
    assert all(x["met"] for x in victory_checks(state, Side.A, "Shitatehineri"))
    state.fighter_a.unstable = True
    assert not all(x["met"] for x in victory_checks(state, Side.A, "Shitatehineri"))


def test_shitate_discard_replay_chooser_lists_actual_cards():
    state = _state()
    state.fighter_a.discard_pile = [card_by_name("Shove"), card_by_name("Gain Right Grip")]
    session = SimpleNamespace(state=state, human_side=Side.A)
    prompt = ChoiceRequired("Shitatehineri", "replay_discard_index", [0, 1])
    shown = labelled_choices(session, prompt)
    assert shown["choice_required"]
    assert "Exhaust" in shown["choice_title"]
    assert [x["card"]["name"] for x in shown["options"]] == ["Shove", "Gain Right Grip"]
    assert [x["value"] for x in shown["options"]] == [0, 1]


def test_new_kimarite_are_not_added_to_the_frozen_v51_pool():
    from kimarite.catalog import CARD_POOL, B11_CARD_POOL
    assert {c.name for c in B11_CARD_POOL} == {"Shitatehineri", "Shitatedashinage"}
    assert not ({c.name for c in B11_CARD_POOL} & {c.name for c in CARD_POOL})
