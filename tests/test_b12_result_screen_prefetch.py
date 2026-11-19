"""B12 results show immediately; AI standings resolve in one background HTTP batch.

These are Node-level control-flow tests, not fake W–L data tests. The real
20-AI-bout engine and atomic 21-result ledger are tested separately.
"""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
JS = (WEB / "client.js").read_text(encoding="utf-8")
HTML = (WEB / "index.html").read_text(encoding="utf-8")
CSS = (WEB / "style.css").read_text(encoding="utf-8")
PREFETCH = "let resolvingB12Matchday=false;" + JS.split(
    "let resolvingB12Matchday=false;", 1
)[1].split("async function commitB12PlayerResult(m){", 1)[0]
RETURN = "async function returnToHeya(){" + JS.split(
    "async function returnToHeya(){", 1
)[1].split("$('result-next').onclick=returnToHeya", 1)[0]


def execute(script):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node not installed")
    proc = subprocess.run([node, "-e", script],
                          capture_output=True, text=True, timeout=20)
    assert proc.returncode == 0, proc.stderr + "\n" + proc.stdout
    return json.loads(proc.stdout.strip().splitlines()[-1])


def browser_stub():
    return """
const buttons=new Map();
function $(id){
 if(!buttons.has(id)) {
  const classes=new Set();
  buttons.set(id,{disabled:false,hidden:false,textContent:'',title:'',
   classList:{toggle:(cls,on)=>on?classes.add(cls):classes.delete(cls),
    contains:cls=>classes.has(cls)},open:false,close(){this.open=false}});
 }
 return buttons.get(id);
}
const management={division_roster:{seed:9,completed_basho:0},division_league:{},round:0,results:[]};
const sessionSetup={seed:9001};
const game={finished:true};
let calls=0;
const pending=[];
function isB12Campaign(m){return !!m?.division_roster}
function activeTournamentBout(){return 0}
function commitB12PlayerResult(m){
 calls++;
 return new Promise((resolve,reject)=>{
  pending.push({
   resolve:()=>{m.results.push({won:true});resolve()},
   reject
  });
 });
}
"""


def test_result_modal_precedes_start_of_real_ai_simulation():
    result = JS.split("function render(g){", 1)[1].split(
        "async function play(hand_index)", 1
    )[0]
    assert result.index("showBoutResult(g);") < result.index("startB12MatchdayPrefetch(g);")
    assert "dialog.showModal()" in JS.split("function showBoutResult(g){", 1)[1].split(
        "$('result-review').onclick", 1
    )[0]
    assert "Simulating the other 20 bouts while you review this result" in JS
    assert 'id="result-standings-status"' in HTML


def test_prefetch_is_single_shared_promise_and_border_only_when_ready():
    code = browser_stub() + PREFETCH + """
(async()=>{
 const first=startB12MatchdayPrefetch(game);
 const second=startB12MatchdayPrefetch(game);
 const during={calls,unready:!$('result-next').classList.contains('heya-standings-ready'),
    loading:$('result-next').classList.contains('heya-standings-loading'),
    title:$('result-next').textContent};
 if(first!==second)throw new Error('Duplicated pending matchday');
 pending[0].resolve();
 await Promise.all([first,second]);
 const ready={calls,records:management.results.length,
  modalReady:$('result-next').classList.contains('heya-standings-ready'),
  hudReady:$('return-heya').classList.contains('heya-standings-ready'),
  button:$('result-next').textContent,
  status:$('result-standings-status').textContent};
 await startB12MatchdayPrefetch(game);
 console.log(JSON.stringify({during,ready,after:calls}));
})().catch(e=>{console.error(e);process.exit(1)});
"""
    result = execute(code)
    assert result["during"]["calls"] == 1
    assert result["during"]["unready"] and result["during"]["loading"]
    assert result["ready"]["calls"] == 1
    assert result["ready"]["records"] == 1
    assert result["ready"]["modalReady"] and result["ready"]["hudReady"]
    assert "Ready" in result["ready"]["button"]
    assert "All 21 matches" in result["ready"]["status"]
    assert result["after"] == 1


def test_failed_background_simulation_has_no_ready_border_and_can_retry():
    code = browser_stub() + PREFETCH + """
(async()=>{
 const first=startB12MatchdayPrefetch(game);
 pending[0].reject(new Error('simulator unavailable'));
 let caught=false;try{await first}catch(e){caught=true}
 const error={caught,ready:$('result-next').classList.contains('heya-standings-ready'),
   records:management.results.length,status:$('result-standings-status').textContent};
 const retry=startB12MatchdayPrefetch(game);
 pending[1].resolve();
 await retry;
 console.log(JSON.stringify({error,calls,ready:$('result-next').classList.contains('heya-standings-ready')}));
})().catch(e=>{console.error(e);process.exit(1)});
"""
    result=execute(code)
    assert result["error"]["caught"]
    assert not result["error"]["ready"]
    assert result["error"]["records"] == 0
    assert "simulator unavailable" in result["error"]["status"]
    assert result["calls"] == 2
    assert result["ready"]


def test_early_return_waits_for_same_simulation_without_launching_a_second_one():
    code = browser_stub() + PREFETCH + RETURN + """
function setGameLocation(p){phase=p}
function managementStatus(){}
function managementBoard(){}
function completedBlock(){return false}
function unresolvedRewards(){return []}
let phase='dohyo';
(async()=>{
 const first=startB12MatchdayPrefetch(game);
 const travel=returnToHeya();
 // The user clicked before the 20-bout calculation finished.
 const waiting={phase,calls,disabled:$('result-next').disabled};
 pending[0].resolve();
 await Promise.all([first,travel]);
 console.log(JSON.stringify({waiting,phase,calls,records:management.results.length}));
})().catch(e=>{console.error(e);process.exit(1)});
"""
    result=execute(code)
    assert result["waiting"] == {"phase":"dohyo","calls":1,"disabled":True}
    assert result["phase"] == "heya"
    assert result["calls"] == 1
    assert result["records"] == 1


def test_ready_border_is_new_ui_and_not_applied_during_calculation():
    assert "#result-next.heya-standings-ready" in CSS
    assert "#return-heya.heya-standings-ready" in CSS
    assert "#result-next.heya-standings-loading" in CSS
    assert "returnToHeya" in JS
