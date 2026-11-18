"""B12 results and Side-by-Side UI are snapshots of actual combat rules."""
from copy import deepcopy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from kimarite.actions import observe
from kimarite.b10_human_session import public_snapshot, side_by_side_snapshot
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.human_bout import HumanBout
from kimarite.models import BoutState, FighterState, GripState, Side, Wrestler
from kimarite.rules import gain_push
from kimarite.tachiai import compare_tachiai
from kimarite.temporary import remove_temporary, resolve_start_of_turn_temporaries

WEB = Path(__file__).resolve().parents[1] / "web"
JS = (WEB / "client.js").read_text(encoding="utf-8")
HTML = (WEB / "index.html").read_text(encoding="utf-8")
CSS = (WEB / "style.css").read_text(encoding="utf-8")


def session(position=0, momentum=0, human_side=Side.A):
    blank = card_by_name("Oshi")
    a = Wrestler("You", 1, 1, 1, blank, blank, blank)
    b = Wrestler("Opponent", 1, 1, 1, blank, blank, blank)
    state = BoutState(FighterState(a), FighterState(b),
                      position=position, momentum=momentum)
    state.b11_explain_wins = True
    state.active_side = human_side
    comp = compare_tachiai(a, b)
    return HumanBout(state, comp, human_side, lambda *_: None)


@pytest.mark.parametrize("winner_side,position", [(Side.A, 4), (Side.B, -4)])
def test_grip_ring_out_yorikiri_has_all_six_numeric_stats(winner_side, position):
    bout = session(position=position, momentum=-2)
    winner = bout.state.fighter(winner_side)
    loser = bout.state.opponent(winner_side)
    winner.left_grip = GripState.GRIP
    winner.power = 8
    winner.hand = [card_by_name("Oshi")] * 4
    loser.hand = [card_by_name("Oshi")]
    gain_push(bout.state, winner_side, 1)
    assert bout.state.winner is winner_side
    assert bout.state.win_method == "Yorikiri"
    info = bout.state.b11_victory_details
    assert info["source"] == "ringout"
    assert info["checks"] == []
    assert "ring boundary" in info["requirement_text"]
    assert info["grip"] == 1
    assert info["effective_grip"] == 1
    assert info["power"] == 8
    assert info["position_advantage"] == 4
    assert info["momentum_advantage"] == -2 * bout.state.sign(winner_side)
    assert info["hand_advantage"] == 3
    browser = public_snapshot(bout)
    assert browser["victory_details"] == info
    assert set(("grip", "effective_grip", "power", "momentum_advantage",
                "position_advantage", "hand_advantage")) <= set(browser["victory_details"])


def test_direct_non_grip_ringout_and_exhaustion_also_have_actual_stats():
    bout = session(position=4)
    bout.state.fighter_a.power = 6
    gain_push(bout.state, Side.A, 1)
    assert bout.state.win_method == "Oshidashi"
    assert bout.state.b11_victory_details["grip"] == 0
    assert bout.state.b11_victory_details["position_advantage"] == 4
    exhausted = session(position=2)
    exhausted.state.declare_winner(Side.A, "Exhaustion")
    assert exhausted.state.win_method == "Koshikudake"
    assert exhausted.state.b11_victory_details["position_advantage"] == 2
    assert exhausted.state.b11_victory_details["effective_grip"] == 0


@pytest.mark.parametrize("card_name", ["Sidestep", "Spin Away"])
@pytest.mark.parametrize("human_side", [Side.A, Side.B])
@pytest.mark.parametrize("momentum", [-2, 0, 2])
def test_side_by_side_snapshot_matches_actual_survival_and_removal(card_name, human_side, momentum):
    owner = human_side
    start_position = 3 if owner is Side.A else -3
    bout = session(position=start_position, momentum=momentum, human_side=human_side)
    resolve_exchange_effect(bout.state, owner, card_by_name(card_name), EffectContext())
    assert bout.state.side_by_side_owner is owner
    assert bout.state.position == 0
    active = side_by_side_snapshot(bout)
    assert active == public_snapshot(bout)["side_by_side"]
    assert active["current_position"] == 0
    assert active["removal_position"] == 0
    assert active["saved_distance"] == 3
    # Spin Away gives the owner +1 Momentum before Side-by-Side starts.
    sign = bout.state.sign(human_side)
    expected_favor = human_side if bout.state.momentum * sign >= 0 else bout.state.opponent_side(human_side)
    assert active["resolution_position"] == bout.state.sign(expected_favor) * sign * 3
    survived = deepcopy(bout.state)
    resolve_start_of_turn_temporaries(survived, owner)
    assert survived.position * sign == active["resolution_position"]
    assert survived.side_by_side_owner is None
    if card_name == "Sidestep":
        assert survived.opponent(owner).unstable
    disrupted = deepcopy(bout.state)
    remove_temporary(disrupted, owner, disrupted.fighter(owner).temporary_zone[0],
                     disrupted=True)
    assert disrupted.position * sign == active["removal_position"]
    assert disrupted.side_by_side_owner is None
    if card_name == "Spin Away":
        assert any(c.name == "Okuritaoshi"
                   for c in disrupted.opponent(owner).kimarite_zone)


def test_opposing_sidesteps_are_readable_from_player_perspective():
    bout = session(position=3, momentum=2)
    resolve_exchange_effect(bout.state, Side.B, card_by_name("Sidestep"), EffectContext())
    live = side_by_side_snapshot(bout)
    assert live["owner"] == "opponent"
    assert live["resolution_position"] == 3  # Opponent owns lock; player has positive Momentum.
    assert live["favorable"] == "human"
    assert live["saved_distance"] == 3


def test_non_side_by_side_snapshot_never_leaks_hidden_information():
    bout = session()
    assert side_by_side_snapshot(bout) is None
    assert public_snapshot(bout)["side_by_side"] is None


def test_ui_contains_explicit_saved_and_projected_positions_and_no_undefined_stats():
    assert 'id="side-by-side-status"' in HTML
    assert 'id="result-standings-status"' in HTML
    assert "side_by_side: side_by_side_snapshot(session)" in (
        Path(__file__).resolve().parents[1] / "src/kimarite/b10_human_session.py"
    ).read_text(encoding="utf-8")
    assert "Position NOW" in JS
    assert "If it survives to its owner’s next turn: Position" in JS
    assert "If removed early: Position" in JS
    assert "The survival prediction changes if Momentum changes" in JS
    assert "signedPosition(side.resolution_position)" in JS
    assert "signedPosition(side.removal_position)" in JS
    assert "value??'—'" in JS
    assert ".side-by-side-status" in CSS


def test_browser_js_parses_after_result_changes():
    node = shutil.which("node")
    if not node:
        pytest.skip("node unavailable")
    p = subprocess.run([node, "--check", str(WEB / "client.js")],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
