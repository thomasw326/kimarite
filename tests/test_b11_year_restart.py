"""A completed six-tournament year can restart without manual storage clearing."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
JS = (WEB / "client.js").read_text(encoding="utf-8")
HTML = (WEB / "index.html").read_text(encoding="utf-8")


def run_restart(previous_count):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required to exercise browser restart")
    start = "$('confirm-new-wrestler').onclick=()=>{"
    end = "$('management-start').onclick="
    handler = start + JS.split(start, 1)[1].split(end, 1)[0]
    stub = f"""
const elements = {{}};
const $=id=>elements[id]??=( {{
 hidden:false,disabled:false,open:false,value:'',textContent:'',
 showModal(){{this.open=true}},close(){{this.open=false}}
}});
const management = {{
 human:'Old Rikishi',opening_mode:'b11_live',
 results:Array.from({{length:15}},()=>({{won:true}})),
 tournament_history:Array.from({{length:{previous_count}}},(_,i)=>({{tournament:i+1,wins:10,losses:5}}))
}};
let activeDraft={{picks:['Oshi']}},token='old',game={{finished:true}},
 sessionSetup={{tournament_bout:14}},actionJournal=[{{type:'end_turn'}}],
 lastPresentedResult='old',cleared=false,phase='';
function yearHistory(m){{return m.tournament_history||[]}}
function managementSave(){{}}
function championshipPending(){{return false}}
function saveDraft(){{}}
function clearBoutSession(){{cleared=true;token=null;game=null;sessionSetup=null;actionJournal=[]}}
function creationChoices(){{}}
function showYearStatus(m){{$('year-record').textContent='Tournament '+(m.tournament_history.length+1)}}
function showB12Banzuke(m){{$('b12-banzuke').hidden=!m}}
function setGameLocation(p){{phase=p}}
"""
    # Existing JS handler reassigns management, so it must be mutable.
    stub = stub.replace("const management = {", "let management = {")
    script = stub + handler + """
$('confirm-new-wrestler').onclick();
console.log(JSON.stringify({
 human:management?.human||null,activeDraft,cleared,phase,
 name:$('wrestler-name').value,
 draftVisible:!$('management-deal').hidden,
 newVisible:!$('new-wrestler').hidden,
 banzukeHidden:$('b12-banzuke').hidden
}));
"""
    r = subprocess.run([node, "-e", script], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_restart_only_after_sixth_tournament():
    before = run_restart(4)
    assert before["human"] == "Old Rikishi"
    assert before["cleared"] is False

    after = run_restart(5)
    assert after["human"] is None
    assert after["activeDraft"] is None
    assert after["cleared"] is True
    assert after["phase"] == "heya"
    assert after["name"] == "Your Rikishi"
    assert after["draftVisible"] is True
    assert after["newVisible"] is False
    assert after["banzukeHidden"] is True


def test_restart_requires_explicit_confirmation_and_warns_about_local_save():
    for name in ["new-wrestler", "new-wrestler-confirm", "cancel-new-wrestler", "confirm-new-wrestler"]:
        assert f'id="{name}"' in HTML
    assert "replaces your current locally saved sumo year" in HTML
    assert "$('new-wrestler').onclick=()" in JS
    assert "$('cancel-new-wrestler').onclick=()" in JS
    assert "yearHistory(management).length<5" in JS
