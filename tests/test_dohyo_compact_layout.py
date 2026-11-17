"""Keep the wrestler state and current card decision together at normal zoom.

The optional Chromium pass renders the actual HTML/CSS in a static fixture.
No live bout, server session, network request or gameplay change is needed.
"""
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
HTML = (WEB / "index.html").read_text(encoding="utf-8")
CSS = (WEB / "style.css").read_text(encoding="utf-8")
JS = (WEB / "client.js").read_text(encoding="utf-8")


class LayoutParser(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img",
            "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.stack = []
        self.parents = {}
        self.attrs = {}

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if props.get("id"):
            self.parents[props["id"]] = [x["classes"] for x in self.stack]
            self.attrs[props["id"]] = props
        if tag not in self.VOID:
            self.stack.append({"tag": tag, "classes": props.get("class", "").split()})

    def handle_endtag(self, tag):
        assert self.stack and self.stack[-1]["tag"] == tag, (
            "Invalid nesting: expected " + (self.stack[-1]["tag"] if self.stack else "nothing")
            + ", closed " + tag
        )
        self.stack.pop()


def test_status_and_decisions_share_primary_bout_layout():
    parser = LayoutParser()
    parser.feed(HTML)
    assert parser.stack == []
    assert "bout-state" in sum(parser.parents["tracks"], [])
    assert "bout-state" in sum(parser.parents["score"], [])
    assert "bout-decisions" in sum(parser.parents["choices"], [])
    assert "bout-decisions" in sum(parser.parents["hand"], [])
    assert "bout-decisions" in sum(parser.parents["notice"], [])
    assert "bout-secondary" in sum(parser.parents["history"], [])
    assert "bout-secondary" in sum(parser.parents["opening"], [])
    assert "bout-decisions" not in sum(parser.parents["history"], [])
    assert "open" not in parser.attrs["bout-history-details"]
    assert "open" not in parser.attrs["opening-details"]
    assert "open" in parser.attrs["dohyo-details"]


def test_layout_prioritizes_status_over_the_event_log():
    assert ".bout-layout{display:grid;grid-template-columns:" in CSS
    assert ".bout-state #score{display:grid;grid-template-columns:" in CSS
    assert ".bout-state .tracks" in CSS
    assert ".bout-decisions #choices" in CSS
    assert ".bout-decisions #hand" in CSS
    assert "@media (min-width:980px) and (min-height:650px)" in CSS
    assert "@media (max-width:979px)" in CSS
    assert "body[data-phase=\"dohyo\"] .bout-hud:not([hidden]){display:block}" in CSS
    assert "$('bout-history-details').open=true" in JS


# The primary cards and game state should fit together on a typical laptop
# viewport at 100% zoom. Chrome/Chromium is not required to run Python rules
# tests on a local machine, but run the browser check when it is installed.
def rendered_layout(width, height):
    chrome = next((shutil.which(name) for name in
                   ("chromium", "google-chrome", "google-chrome-stable", "chromium-browser")
                   if shutil.which(name)), None)
    if not chrome:
        pytest.skip("Chrome/Chromium unavailable for optional real-browser layout assertion")

    fixture = HTML.replace(
        '<link rel="stylesheet" href="/style.css">', "<style>" + CSS + "</style>"
    ).replace('<script src="/client.js"></script>', "")
    setup = """
<script>
document.body.dataset.phase='dohyo';
document.querySelector('#heya-view').hidden=true;
document.querySelector('#dohyo-view').hidden=false;
document.querySelector('#phase-heading').textContent='Dohyō · The Ring';
document.querySelector('#round').textContent='TURN 3 · EXCHANGE';
document.querySelector('#tracks').innerHTML=
 '<span class="track">POSITION +2</span><span class="track">MOMENTUM +1</span>';
document.querySelector('#ring-position-label').textContent='Position +2 · Advancing';
const fighter=(name)=>`<div class="rikishi-info"><div class="eyebrow">STATE</div>
 <h2>${name}</h2><p>Power 4 · Grip 1/1 · Plays 2</p>
 <p class="zones"><b>Kimarite:</b> Oshidashi, Yorikiri<br>
 <b>Temporary:</b> Gain Left Grip, Sonkyo</p>
 <button class="discard-button">Discard pile: 7 · View cards</button>
 <div class="zone-list"><div class="zone-entry"><button class="zone-card">Oshidashi · Inspect</button>
 <p class="temporary-detail">Detailed effect available on inspection.</p></div>
 <div class="zone-entry"><button class="zone-card">Gain Left Grip · Inspect</button></div></div></div>`;
document.querySelector('#score').innerHTML=fighter('Your Rikishi')+fighter('Opponent');
const card=(label)=>`<div class="choice-card-wrap">
 <button class="card">${label}<div class="orb">POWER 1 · TECH 1</div></button>
 <button class="choice-inspect">Inspect</button></div>`;
document.querySelector('#choices').innerHTML=
 '<h2>Choose 2 cards to keep</h2><p>Pick cards for your hand.</p>'
 +'<div class="cards">'+card('Oshi')+card('Tsuki')+card('Yori')+'</div>'
 +'<button class="confirm">Keep selected cards</button>';
document.querySelector('#hand').innerHTML=
 '<button class="card">Oshi</button><button class="card">Tsuki</button>'
 +'<button class="card">Yori</button><button class="card">Sonkyo</button>';
const r=(selector)=>{let x=document.querySelector(selector).getBoundingClientRect();
return {top:Math.round(x.top),bottom:Math.round(x.bottom),left:Math.round(x.left),
right:Math.round(x.right),height:Math.round(x.height)}};
const result={
 width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth,
 state:r('.bout-state'),decision:r('.bout-decisions'),
 choices:r('#choices'),score:r('#score'),tracks:r('#tracks'),hand:r('.play'),
 thirdChoice:r('#choices .choice-card-wrap:nth-child(3)'),
 historyOpen:document.querySelector('#bout-history-details').open
};
document.body.insertAdjacentHTML('beforeend',
 '<output id="layout-metrics">'+JSON.stringify(result)+'</output>');
</script>
"""
    fixture = fixture.replace("</body>", setup + "</body>")
    with TemporaryDirectory() as directory:
        path = Path(directory) / "layout.html"
        path.write_text(fixture, encoding="utf-8")
        result = subprocess.run([
            chrome, "--headless", "--no-sandbox", "--disable-gpu",
            "--disable-dev-shm-usage", "--hide-scrollbars",
            f"--window-size={width},{height}", "--virtual-time-budget=700",
            "--dump-dom", path.as_uri(),
        ], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr[-1000:]
    found = re.search(r'<output id="layout-metrics">([^<]+)</output>', result.stdout)
    assert found, result.stdout[-2000:]
    return json.loads(unescape(found.group(1)))


@pytest.mark.parametrize("width,height", [(1366, 768), (1280, 800)])
def test_laptop_view_keeps_combat_decisions_and_state_in_view(width, height):
    layout = rendered_layout(width, height)
    assert layout["historyOpen"] is False
    assert layout["decision"]["left"] > layout["state"]["right"] - 2
    assert abs(layout["state"]["top"] - layout["choices"]["top"]) <= 35
    for key in ("tracks", "score", "choices", "hand"):
        assert layout[key]["top"] >= 0
        assert layout[key]["top"] < layout["height"] - 40, (key, layout)
    assert layout["thirdChoice"]["right"] <= layout["width"], layout
    assert layout["hand"]["bottom"] <= layout["height"], layout
    assert layout["scrollWidth"] <= layout["width"] + 2, layout


def test_mobile_layout_keeps_action_area_without_page_width_overflow():
    layout = rendered_layout(390, 844)
    assert layout["decision"]["top"] < layout["state"]["top"]
    assert layout["scrollWidth"] <= layout["width"] + 2, layout
