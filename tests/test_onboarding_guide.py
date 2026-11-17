"""First-launch guide should not interrupt saved play, and must be reopenable."""
from html.parser import HTMLParser
from pathlib import Path
import json
import shutil
import subprocess

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
JS = (WEB / "client.js").read_text(encoding="utf-8")
HTML = (WEB / "index.html").read_text(encoding="utf-8")
CSS = (WEB / "style.css").read_text(encoding="utf-8")


class IDs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = {}

    def handle_starttag(self, tag, attrs):
        vals = dict(attrs)
        if "id" in vals:
            self.tags[vals["id"]] = (tag, vals)


def run_guide(saved):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required to execute the browser onboarding logic")
    helper = "function shouldShowGameGuide(){" + JS.split(
        "function shouldShowGameGuide(){", 1
    )[1].split("function clearBoutSession(){", 1)[0]
    script = """
const values=new Map(Object.entries(JSON.parse(process.argv[1])));
const gameSaveGet=key=>values.has(key)?values.get(key):null;
const gameSaveSet=(key,value)=>values.set(key,value);
const elements={};
const $=id=>elements[id]??=( {
 open:false,
 handlers:{},
 showModal(){this.open=true},
 close(){
  this.open=false;
  (this.handlers.close||[]).forEach(fn=>fn());
 },
 addEventListener(name,fn){(this.handlers[name]??=[]).push(fn)}
});
""" + helper + """
installGameGuide();
const shownInitially=$('game-guide').open;
$('guide-dismiss').onclick();
const seenAfterDismiss=gameSaveGet('kimarite_guide_seen');
$('open-game-guide').onclick();
console.log(JSON.stringify({
 shownInitially,seenAfterDismiss,shownAfterReopen:$('game-guide').open,
 seenAfterReopen:gameSaveGet('kimarite_guide_seen')
}));
"""
    result = subprocess.run(
        [node, "-e", script, json.dumps(saved)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_guide_is_accessible_and_available_from_both_locations():
    parser = IDs()
    parser.feed(HTML)
    assert parser.tags["game-guide"][0] == "dialog"
    assert parser.tags["open-game-guide"][1]["aria-controls"] == "game-guide"
    assert parser.tags["open-game-guide"][1]["aria-haspopup"] == "dialog"
    assert parser.tags["game-guide"][1]["aria-labelledby"] == "game-guide-title"
    assert parser.tags["guide-dismiss"][0] == "button"
    assert HTML.index('id="open-game-guide"') < HTML.index('id="heya-view"')
    for phrase in (
        "Heya", "Dohyō", "Tachiai", "Kimarite", "Exchange",
        "six tournaments of 15 bouts", "up to 12", "±4",
    ):
        # Ring bounds are described as +4/−4 rather than the ± shorthand.
        if phrase == "±4":
            assert "Position +4 or −4" in HTML
        else:
            assert phrase in HTML
    assert ".game-guide-dialog" in CSS
    assert ".game-guide-trigger" in CSS
    assert JS.rstrip().endswith("installGameGuide();")


@pytest.mark.parametrize("saved,expected", [
    ({}, True),
    ({"kimarite_management": "null"}, True),
    ({"kimarite_active_draft": "null"}, True),
    ({"kimarite_management": '{"round":2}'}, False),
    ({"kimarite_active_draft": '{"picks":[]}'}, False),
    ({"kimarite_session": "active-token"}, False),
    ({"kimarite_guide_seen": "1"}, False),
])
def test_first_run_guide_respects_saves_and_can_be_reopened(saved, expected):
    result = run_guide(saved)
    assert result == {
        "shownInitially": expected,
        "seenAfterDismiss": "1",
        "shownAfterReopen": True,
        "seenAfterReopen": "1",
    }
