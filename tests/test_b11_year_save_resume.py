"""Wrestler-year saves persist across tabs/browser restart and avoid stale bout replay."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

JS = (Path(__file__).resolve().parents[1] / "web" / "client.js").read_text(encoding="utf-8")


def call_save_helpers(script):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node needed for browser storage regression")
    helper = "const playtestSavePrefix='';function gameSaveGet(key){" + JS.split("function gameSaveGet(key){", 1)[1].split(
        "function returnedToHeyaAfterBout(g){", 1
    )[0]
    prep = """
const session=new Map(),persist=new Map();
const sessionStorage={
 getItem:key=>session.has(key)?session.get(key):null,
 setItem:(key,v)=>session.set(key,v),
 removeItem:key=>session.delete(key)
};
const localStorage={
 getItem:key=>persist.has(key)?persist.get(key):null,
 setItem:(key,v)=>persist.set(key,v),
 removeItem:key=>persist.delete(key)
};
let token='last_token',game={finished:true},sessionSetup={seed:123},actionJournal=[{type:'end_turn'}];
"""
    output = subprocess.run([node, "-e", prep + helper + script], capture_output=True, text=True)
    assert output.returncode == 0, output.stderr
    return json.loads(output.stdout)


def test_management_saves_survive_browser_session_reset():
    result = call_save_helpers("""
const sample={human:'My Rikishi',created_stats:{power:2,technique:1,spirit:0},
 tournament_history:[{tournament:1,wins:8,losses:7}],round:0,results:[]};
gameSaveSet('kimarite_management',JSON.stringify(sample));
session.clear(); // a new browser session retains localStorage
console.log(JSON.stringify(JSON.parse(gameSaveGet('kimarite_management'))));
""")
    assert result["human"] == "My Rikishi"
    assert result["created_stats"] == {"power": 2, "technique": 1, "spirit": 0}
    assert result["tournament_history"][0]["wins"] == 8


def test_current_tab_overrides_stale_saved_state():
    result = call_save_helpers("""
gameSaveSet('kimarite_management',JSON.stringify({round:2}));
persist.set('kimarite_management',JSON.stringify({round:0}));
console.log(JSON.stringify(JSON.parse(gameSaveGet('kimarite_management'))));
""")
    assert result == {"round": 2}


def test_new_tournament_removes_stale_finished_bout_state():
    result = call_save_helpers("""
for(const key of ['kimarite_session','kimarite_setup','kimarite_actions'])
 gameSaveSet(key,'old bout');
clearBoutSession();
console.log(JSON.stringify({
 token,game,setup:sessionSetup,journal:actionJournal,
 tokenSave:gameSaveGet('kimarite_session'),
 setupSave:gameSaveGet('kimarite_setup'),
 actionsSave:gameSaveGet('kimarite_actions')
}));
""")
    assert result == {
        "token": None, "game": None, "setup": None, "journal": [],
        "tokenSave": None, "setupSave": None, "actionsSave": None,
    }


def test_phase_and_draft_resume_take_precedence_over_old_bout():
    assert "gameSaveSet('kimarite_ui_phase',location)" in JS
    assert "gameSaveGet('kimarite_ui_phase')!=='heya'" in JS
    assert "function managementSave(){gameSaveSet('kimarite_management',JSON.stringify(management))}" in JS
    assert "function saveDraft(){if(activeDraft)gameSaveSet('kimarite_active_draft'" in JS
    assert "if(JSON.parse(gameSaveGet('kimarite_active_draft')||'null')){setGameLocation('heya');return}" in JS
    assert "const saved=JSON.parse(gameSaveGet('kimarite_management')||'null')" in JS
    assert "const pending=JSON.parse(gameSaveGet('kimarite_active_draft')||'null')" in JS
    assert "activeDraft=null;saveDraft();\n clearBoutSession();" in JS
    assert "m.cards=data.cards;m.deck_size=data.deck_size;m.groups=Array.from({length:3},()=>[null,null,null]);clearBoutSession();" in JS


def test_next_basho_retains_saved_rematch_rewards_by_opponent_id():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node needed for browser storage regression")
    summary = JS[JS.index("function yearHistory("):JS.index("function showYearStatus(")]
    lookup = JS[JS.index("function savedRematchCard("):JS.index("async function managementRound(")]
    run = subprocess.run([node, "-e", summary + lookup + """
const assert = require('node:assert/strict');
const results = Array.from({length:15}, (_,i)=>({
 opponent_id:'wrestler-'+i,opponent:'Opponent '+i,won:i!==0,
 rematch_top_card:i===0?'Ottsuke':null
}));
const history=JSON.parse(JSON.stringify([tournamentSummary({results})]));
const next={tournament_history:history,results:[]};
assert.equal(savedRematchCard(next,'wrestler-0'),'Ottsuke');
assert.equal(savedRematchCard(next,'wrestler-1'),null);
next.results.push({opponent_id:'wrestler-0',won:true});
assert.equal(savedRematchCard(next,'wrestler-0'),null);
"""], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
