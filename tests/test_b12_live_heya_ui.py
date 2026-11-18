"""Browser integration checks for current B12 standings and player result flow."""
from pathlib import Path
import shutil
import subprocess

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
JS = (WEB / "client.js").read_text(encoding="utf-8")
HTML = (WEB / "index.html").read_text(encoding="utf-8")
CSS = (WEB / "style.css").read_text(encoding="utf-8")


def test_b12_browser_javascript_parses():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is not available")
    run = subprocess.run([node, "--check", str(WEB / "client.js")],
                         text=True, capture_output=True)
    assert run.returncode == 0, run.stderr


def test_new_drafted_wrestler_uses_live_b12_campaign_instead_of_preset_opponents():
    finish = JS.split("async function finishDraft(){", 1)[1].split(
        "$('management-deal').onclick=", 1
    )[0]
    assert "/api/b12/campaign/new" in finish
    assert "/api/b12/campaign/plan" in finish
    assert "assignB12Block(management,division)" in finish
    assert "b12_opponent_ids:Array(15).fill(null)" in finish
    assert "division_roster:division.roster" in finish
    assert "division_league:division.league" in finish
    assert "opponents:roster.slice(0,15)" not in finish


def test_three_known_opponents_rank_record_style_and_optional_testing_details():
    board = JS.split("function managementBoard(){", 1)[1].split(
        "async function managementRound", 1
    )[0]
    assert "b12OpponentLabel(m,bout)" in board
    assert "opponentInfo.format_description" in board
    assert "Testing: opponent deck format" in board
    assert "if(allocationLockState(m,group))" not in board
    assert "showB12Banzuke(m)" in board
    assert 'id="b12-banzuke"' in HTML
    assert 'id="b12-banzuke-entries"' in HTML
    assert 'id="b12-banzuke-heading"' in HTML
    assert ".banzuke-entry.banzuke-player" in CSS
    assert "max-height:320px" in CSS


def test_player_does_not_advance_a_b12_day_without_all_twenty_simulated_bouts():
    status = JS.split("function managementStatus(){", 1)[1].split(
        "let playerShikonaPool", 1
    )[0]
    assert "if(!isB12Campaign(m)&&game&&game.finished" in status
    commit = JS.split("async function commitB12PlayerResult(m){", 1)[1].split(
        "async function returnToHeya(){", 1
    )[0]
    assert "/api/b12/campaign/resolve" in commit
    assert "resolved.ai_matches!==20" in commit
    assert "resolved.league?.day!==i+1" in commit
    assert "m.division_league=resolved.league" in commit
    assert commit.index("m.division_league=resolved.league") < commit.index("m.results.push(record)")
    assert "recoverSession()" in commit
    returned = JS.split("async function returnToHeya(){", 1)[1].split(
        "$('result-next').onclick=returnToHeya", 1
    )[0]
    assert returned.index("await commitB12PlayerResult(management)") < returned.index("setGameLocation('heya')")


def test_tournament_boundary_and_round_repair_have_real_canonical_state():
    setup = JS.split("$('management-deal').onclick=async", 1)[1].split(
        "$('management-new').onclick", 1
    )[0]
    assert "/api/b12/campaign/advance" in setup
    assert "division_roster:division?.roster||null" in setup
    assert "division_league:division?.league||null" in setup
    next_block = JS.split("$('management-next').onclick=async", 1)[1].split(
        "function renderBoutHud", 1
    )[0]
    assert "/api/b12/campaign/plan" in next_block
    assert "assignB12Block(m,planned)" in next_block
    fight = JS.split("async function managementRound(){", 1)[1].split(
        "function earnedNextStartingCards()", 1
    )[0]
    assert "/api/b12/campaign/pair" in fight
    assert "request.b12_opponent_ai=paired.opponent" in fight
    assert "request.b12_player_rank=m.division_roster.player.rank" in fight
    assert "request.b12_campaign=" in fight
    assert "managementSave(); // Persist frozen 21-pair day" in fight
