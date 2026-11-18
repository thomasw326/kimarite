"""B12 browser reset button and explicit ?fresh=1 clean-start URL.

Both sessionStorage and localStorage hold game state. The reset must remove
both, clear a live bout as well as a pending 28-card draft, and run before
the asynchronous save-restore code. It must not touch unrelated site data.
"""
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
SAVE_KEYS = (
    "kimarite_management",
    "kimarite_active_draft",
    "kimarite_session",
    "kimarite_setup",
    "kimarite_actions",
    "kimarite_ui_phase",
)


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = {}

    def handle_starttag(self, tag, attrs):
        properties = dict(attrs)
        if "id" in properties:
            self.ids[properties["id"]] = (tag, properties)


def test_reset_control_is_always_visible_and_requires_explicit_confirmation():
    elements = Elements()
    elements.feed(HTML)
    trigger = elements.ids["reset-progress"]
    assert trigger[0] == "button"
    assert trigger[1]["type"] == "button"
    assert trigger[1]["aria-controls"] == "reset-progress-confirm"
    assert trigger[1]["aria-haspopup"] == "dialog"
    assert HTML.index('id="reset-progress"') < HTML.index("</header>")
    assert elements.ids["reset-progress-confirm"][0] == "dialog"
    assert elements.ids["reset-cancel"][1]["type"] == "button"
    assert elements.ids["reset-confirm"][1]["type"] == "button"
    assert "cannot be undone" in HTML
    assert ".reset-progress-trigger" in CSS
    assert "max-width:560px" in CSS


def test_reset_runs_before_any_existing_game_is_loaded():
    assert JS.index("resetFromCleanLink();") < JS.index("resume();")
    assert JS.index("resetFromCleanLink();") < JS.index("api('/api/roster').then(")
    assert "params.get('fresh')!=='1'" in JS
    assert "params.delete('fresh')" in JS
    assert "window.history.replaceState" in JS
    assert "window.location.replace(window.location.pathname+'?fresh=1')" in JS
    assert "clearSavedProgress();" in JS


def run_js(start_query: str, interactions: str):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to verify the browser reset behavior")
    reset_code = "const RESET_PROGRESS_KEYS=Object.freeze([" + JS.split(
        "const RESET_PROGRESS_KEYS=Object.freeze([", 1
    )[1].split("function rememberSession()", 1)[0]
    script = """
const sessionMap=new Map();
const localMap=new Map();
const keys=['kimarite_management','kimarite_active_draft','kimarite_session',
            'kimarite_setup','kimarite_actions','kimarite_ui_phase',
            'kimarite_guide_seen','unrelated_site_key'];
for(const key of keys){
 sessionMap.set(key,'old-session-'+key);
 localMap.set(key,'old-local-'+key);
}
const removed=[];
function gameSaveRemove(key){
 removed.push(key);
 sessionMap.delete(key);
 localMap.delete(key);
}
const controls={};
const $=id=>controls[id]??={
 open:false,
 showModal(){this.open=true},
 close(){this.open=false}
};
let changedUrl=null,reloadedUrl=null;
const window={
 location:{pathname:'/',search:START_QUERY,hash:'#heya',
    replace(url){reloadedUrl=url}},
 history:{replaceState(_state,_title,url){changedUrl=url}}
};
""" .replace("START_QUERY", json.dumps(start_query))
    script += reset_code + "\n" + interactions + """
console.log(JSON.stringify({
 removed,session:[...sessionMap.keys()],local:[...localMap.keys()],
 changedUrl,reloadedUrl,dialogOpen:$('reset-progress-confirm').open
}));
"""
    result = subprocess.run([node, "-e", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_fresh_link_clears_both_game_storage_layers_without_touching_other_keys():
    output = run_js("?fresh=1", "")
    assert set(output["removed"]) == set(SAVE_KEYS)
    assert output["session"] == ["kimarite_guide_seen", "unrelated_site_key"]
    assert output["local"] == ["kimarite_guide_seen", "unrelated_site_key"]
    assert output["changedUrl"] == "/#heya"
    assert output["reloadedUrl"] is None


def test_fresh_link_preserves_other_query_parameters_and_does_not_loop():
    output = run_js("?fresh=1&inspector=true", "")
    assert set(output["removed"]) == set(SAVE_KEYS)
    assert output["changedUrl"] == "/?inspector=true#heya"
    assert output["reloadedUrl"] is None
    other = run_js("?fresh=0", "")
    assert other["removed"] == []
    assert len(other["session"]) == 8
    assert len(other["local"]) == 8
    assert other["changedUrl"] is None


def test_button_cancel_keeps_progress_and_confirm_restarts_cleanly():
    cancel = run_js("", """
$('reset-progress').onclick();
if(!$('reset-progress-confirm').open)throw new Error('No confirmation dialog');
$('reset-cancel').onclick();
""")
    assert cancel["removed"] == []
    assert len(cancel["local"]) == 8
    assert not cancel["dialogOpen"]
    assert cancel["reloadedUrl"] is None

    confirm = run_js("", """
$('reset-progress').onclick();
$('reset-confirm').onclick();
""")
    assert set(confirm["removed"]) == set(SAVE_KEYS)
    assert confirm["session"] == ["kimarite_guide_seen", "unrelated_site_key"]
    assert confirm["local"] == ["kimarite_guide_seen", "unrelated_site_key"]
    assert not confirm["dialogOpen"]
    assert confirm["reloadedUrl"] == "/?fresh=1"


def test_clean_link_is_not_required_for_existing_legacy_restart_button():
    # End-of-sixth-basho reset remains available and unchanged.
    assert "$('new-wrestler').onclick=()=>" in JS
    assert "$('confirm-new-wrestler').onclick=()=>" in JS
    assert "if(!management||management.results.length!==15||yearHistory(management).length<5)return" in JS
