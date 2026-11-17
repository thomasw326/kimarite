"""Live Dohyō ring mirrors actual shared Position without changing ring rules."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1] / "web"
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "client.js").read_text(encoding="utf-8")
CSS = (ROOT / "style.css").read_text(encoding="utf-8")


def run_ring_helper(snapshot):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is needed to execute the browser ring updater")
    body = JS.split("function updateDohyoPosition(g){", 1)[1].split(
        "function renderPendingTachiai(g){", 1
    )[0]
    function = "function updateDohyoPosition(g){" + body
    stub = """
const elements={};
const $=id=>elements[id]??=( {
    style:{properties:{},setProperty(k,v){this.properties[k]=v}},
    classList:{classes:{},toggle(k,v){this.classes[k]=v}},
    setAttribute(k,v){this[k]=v}
});
"""
    script = stub + function + """
const snapshot=JSON.parse(process.argv[1]);
updateDohyoPosition(snapshot);
const ring=$('dohyo-ring');
console.log(JSON.stringify({
    shift:ring.style.properties['--ring-shift'],
    edge:!!ring.classList.classes['dohyo-edge'],
    positionText:$('ring-position-label').textContent,
    warningHidden:$('ring-edge-warning').hidden,
    label:ring['aria-label']
}));
"""
    r = subprocess.run(
        [node, "-e", script, json.dumps(snapshot)],
        capture_output=True, text=True, check=False
    )
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@pytest.mark.parametrize("position,shift,edge", [
    (-4, "-24%", True),
    (-3, "-18%", False),
    (-1, "-6%", False),
    (0, "0%", False),
    (1, "6%", False),
    (3, "18%", False),
    (4, "24%", True),
])
def test_dohyo_marker_tracks_shared_position(position, shift, edge):
    result = run_ring_helper({"position": position, "finished": False})
    assert result["shift"] == shift
    assert result["edge"] is edge
    assert result["warningHidden"] is not edge
    assert f"Position {position:+}" in result["positionText"] if position != 0 else (
        "Position 0" in result["positionText"]
    )


def test_edge_is_danger_not_an_automatic_ringout():
    result = run_ring_helper({"position": 4, "finished": False})
    assert result["edge"] is True
    assert "Advancing toward the opponent" in result["positionText"]
    assert "Position +4" in result["label"]
    # Actual ring-out occurs when a fifth Push crosses the boundary.
    done = run_ring_helper({"position": 4, "finished": True})
    assert done["warningHidden"] is True


def test_negative_position_means_human_is_threatened():
    result = run_ring_helper({"position": -4, "finished": False})
    assert "Being pushed toward your edge" in result["positionText"]


@pytest.mark.parametrize("snapshot", [
    {"phase": "choose_tachiai"},
    {"position": None},
    {"position": 5},
    {"position": -5},
])
def test_unknown_or_unrevealed_position_stays_neutral(snapshot):
    result = run_ring_helper(snapshot)
    assert result["shift"] == "0%"
    assert result["edge"] is False
    assert result["warningHidden"] is True
    assert "awaiting Tachiai" in result["positionText"]


def test_live_ring_is_visible_accessible_and_refreshed_by_both_phases():
    assert 'id="dohyo-details" open' in HTML
    assert 'id="dohyo-ring" class="dohyo" role="img"' in HTML
    assert 'id="ring-position-label" class="ring-position-label" role="status"' in HTML
    assert 'id="ring-edge-warning" class="ring-edge-warning" hidden' in HTML
    assert 'id="return-heya"' in HTML
    assert "function renderPendingTachiai(g){\n updateDohyoPosition(g);" in JS
    assert "return}updateDohyoPosition(g);const alreadyInHeya=" in JS
    assert ".dohyo-edge" in CSS
    assert "@media(prefers-reduced-motion:reduce)" in CSS
