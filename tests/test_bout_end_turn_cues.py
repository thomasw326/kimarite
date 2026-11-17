"""End Turn highlights use the engine's actual winning Kimarite checks."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from kimarite.b10_human_session import new_b10_session, public_snapshot
from kimarite.catalog import card_by_name

WEB = Path(__file__).resolve().parents[1] / "web"
JS = (WEB / "client.js").read_text(encoding="utf-8")
CSS = (WEB / "style.css").read_text(encoding="utf-8")


def ready_oshidashi_session():
    session = new_b10_session("Arm Controller", "The Technician", seed=42)
    own = session.state.fighter(session.human_side)
    own.kimarite_zone = [card_by_name("Oshidashi")]
    own.plays_remaining = 0
    session.state.position = 3 * session.state.sign(session.human_side)
    session.state.momentum = 2 * session.state.sign(session.human_side)
    session.state.active_side = session.human_side
    session.awaiting_human = True
    session.pending_selection = None
    session.state.winner = None
    session.stopped_reason = None
    return session


def test_engine_reports_ready_kimarite_when_end_turn_would_win():
    session = ready_oshidashi_session()
    snapshot = public_snapshot(session)
    assert snapshot["can_end_turn"]
    assert snapshot["human"]["plays_remaining"] == 0
    assert snapshot["human"]["ready_kimarite"] == ["Oshidashi"]
    session.end_turn()
    assert session.state.winner is session.human_side
    assert session.state.win_method == "Oshidashi"
    assert public_snapshot(session)["human"]["ready_kimarite"] == []


def test_ready_cue_uses_exact_predicate_not_older_description_threshold():
    session = ready_oshidashi_session()
    session.state.position = 2 * session.state.sign(session.human_side)
    assert public_snapshot(session)["human"]["ready_kimarite"] == []
    session.state.position = 3 * session.state.sign(session.human_side)
    session.state.momentum = 1 * session.state.sign(session.human_side)
    assert public_snapshot(session)["human"]["ready_kimarite"] == []


def test_ready_kimarite_does_not_appear_when_human_cannot_end_turn():
    session = ready_oshidashi_session()
    session.awaiting_human = False
    snapshot = public_snapshot(session)
    assert snapshot["human"]["ready_kimarite"] == []
    assert not snapshot["can_end_turn"]


def test_opponent_ready_kimarite_never_highlights_human_zone():
    session = ready_oshidashi_session()
    own = session.state.fighter(session.human_side)
    foe = session.state.opponent(session.human_side)
    own.kimarite_zone.clear()
    foe.kimarite_zone = [card_by_name("Oshidashi")]
    assert public_snapshot(session)["human"]["ready_kimarite"] == []


def run_cues(state):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required to execute browser cue helper")
    code = "function kimariteTurnCues(g){" + JS.split(
        "function kimariteTurnCues(g){", 1
    )[1].split("function render(g){", 1)[0]
    result = subprocess.run(
        [node, "-e",
         code + "\nconsole.log(JSON.stringify(kimariteTurnCues(JSON.parse(process.argv[1]))));",
         json.dumps(state)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("snapshot,expected", [
    ({"can_end_turn": True, "finished": False,
      "human": {"plays_remaining": 0, "ready_kimarite": []}},
     {"noPlays": True, "readyNames": [], "winReady": False}),
    ({"can_end_turn": True, "finished": False,
      "human": {"plays_remaining": 1, "ready_kimarite": ["Oshidashi"]}},
     {"noPlays": False, "readyNames": ["Oshidashi"], "winReady": True}),
    ({"can_end_turn": True, "finished": False,
      "human": {"plays_remaining": 0,
                "ready_kimarite": ["Oshidashi", "Yorikiri", "Oshidashi"]}},
     {"noPlays": True, "readyNames": ["Oshidashi", "Yorikiri"], "winReady": True}),
    ({"can_end_turn": False, "finished": False,
      "human": {"plays_remaining": 0, "ready_kimarite": ["Oshidashi"]}},
     {"noPlays": False, "readyNames": [], "winReady": False}),
    ({"can_end_turn": True, "finished": True,
      "human": {"plays_remaining": 0, "ready_kimarite": ["Oshidashi"]}},
     {"noPlays": False, "readyNames": [], "winReady": False}),
])
def test_ui_cue_conditions(snapshot, expected):
    assert run_cues(snapshot) == expected


def test_border_and_zone_highlight_tied_to_canonical_snapshot():
    assert "endButton.classList.toggle('end-turn-no-plays',turnCues.noPlays)" in JS
    assert "endButton.classList.toggle('end-turn-win',canFinish)" in JS
    assert "const ready=own&&zoneName==='kimarite'&&readyNames.has(c.name)" in JS
    assert "if(ready)item.append(node('span','kimarite-ready-cue','End turn to win'))" in JS
    assert "'End turn to win':'End turn'" in JS
    assert "$('end').classList.remove('end-turn-no-plays','end-turn-win')" in JS
    assert "#end.end-turn-no-plays:not(:disabled)" in CSS
    assert "#end.end-turn-win:not(:disabled)" in CSS
    assert "#score .zone-card.kimarite-ready" in CSS
