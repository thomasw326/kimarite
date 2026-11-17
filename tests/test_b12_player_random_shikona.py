"""Player shikona shortcut uses the same fictional pool as the B12 AI roster."""
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.request import urlopen
import json
import shutil
import subprocess

import pytest

from kimarite.b10_web import Handler
from kimarite.b12_division_roster import load_shikona

ROOT = Path(__file__).resolve().parents[1] / "web"
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
CLIENT = (ROOT / "client.js").read_text(encoding="utf-8")
CSS = (ROOT / "style.css").read_text(encoding="utf-8")


class Controls(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.elements[attrs["id"]] = (tag, attrs)


def test_random_name_button_is_optional_and_input_stays_editable():
    p = Controls()
    p.feed(HTML)
    field, button = p.elements["wrestler-name"], p.elements["random-wrestler-name"]
    assert field[0] == "input"
    assert field[1]["type"] == "text"
    assert field[1]["maxlength"] == "32"
    assert "readonly" not in field[1]
    assert button[0] == "button"
    assert button[1]["type"] == "button"  # Must not submit or launch the draft.
    assert "random" in button[1]["aria-label"].lower()
    assert p.elements["random-name-status"][1]["role"] == "status"
    assert ".wrestler-name-controls" in CSS
    assert "max-width:440px" in CSS
    assert "const draftedName=$('wrestler-name').value.trim()" in CLIENT


def test_name_pool_http_is_shared_with_ai_roster_not_real_wrestler_profiles():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with urlopen(f"http://127.0.0.1:{server.server_port}/api/shikona", timeout=15) as res:
            assert res.status == 200
            assert res.headers["Content-Type"].startswith("application/json")
            payload = json.load(res)
        assert payload["names"] == load_shikona()
        assert len(payload["names"]) >= 250
        assert len(set(name.casefold() for name in payload["names"])) == len(payload["names"])
        assert {"Gozan", "Kagehayate", "Fukamori"} <= set(payload["names"])
        assert not {"Onosato", "Hoshoryu", "Kirishima"} & set(payload["names"])
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def run_picker(js_expression):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for browser helper behavior")
    part = CLIENT.split("let playerShikonaPool=null;", 1)[1].split(
        "const CREATED_STAT_NAMES=", 1
    )[0]
    script = """
const elements = {};
const $ = id => elements[id] ??= {value:'',textContent:'',disabled:false};
let requests = 0;
let fail = false;
async function api(path) {
    if(path !== '/api/shikona') throw new Error('Wrong endpoint');
    requests++;
    if(fail) throw new Error('Offline');
    return {names:['Gozan','Kagehayate','Sano']};
}
Math.random = () => 0;
""" + "let playerShikonaPool=null;" + part + "\n" + js_expression
    run = subprocess.run([node, "-e", script], text=True, capture_output=True)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def test_random_button_selects_different_name_from_current_and_caches_pool():
    result = run_picker("""
(async () => {
  $('wrestler-name').value='Gozan';
  await $('random-wrestler-name').onclick();
  const first=$('wrestler-name').value;
  const firstNotice=$('random-name-status').textContent;
  await $('random-wrestler-name').onclick();
  console.log(JSON.stringify({first,second:$('wrestler-name').value,
      requests,disabled:$('random-wrestler-name').disabled,firstNotice}));
})().catch(e=>{console.error(e);process.exit(1)});
""")
    assert result == {
        "first": "Kagehayate",
        "second": "Gozan",
        "requests": 1,
        "disabled": False,
        "firstNotice": "Random shikona selected. You can still edit it.",
    }


def test_random_picker_handles_fetch_error_without_erasing_typed_name():
    result = run_picker("""
(async () => {
  $('wrestler-name').value='Custom Name';
  fail=true;
  await $('random-wrestler-name').onclick();
  console.log(JSON.stringify({name:$('wrestler-name').value,
      error:$('random-name-status').textContent,
      disabled:$('random-wrestler-name').disabled}));
})().catch(e=>{console.error(e);process.exit(1)});
""")
    assert result["name"] == "Custom Name"
    assert "Could not choose" in result["error"]
    assert result["disabled"] is False
