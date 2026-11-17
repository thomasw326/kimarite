"""A three-bout block commits each played opening while future cards may swap.

Execute the actual browser allocation helpers with Node, not a copied Python
implementation. This protects legacy saves, physical card identity, and
reloading after any completed bout.
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


def fixture(*, results=0, round=0, groups=None, locks=None, classic=False):
    cards = [{"name": f"Card {i // 2}", "deal_index": i,
              "is_kimarite": i % 3 == 0} for i in range(9)]
    first = (round // 3) * 3
    records = [
        {"assigned_cards": [{"deal_index": i} for i in range(3 * k, 3 * k + 3)]}
        for k in range(min(results, 3))
    ]
    if first:
        records = [{"assigned_cards": []} for _ in range(first)] + records
    return {
        "human": "Rikishi", "opening_mode": "classic" if classic else "b11_live",
        "round": round, "results": records, "cards": cards,
        "groups": groups if groups is not None else [[0, 1, 2], [3, 4, 5], [6, 7, 8]],
        "locked_bouts": locks or {},
        "opponents": [f"Opponent {i}" for i in range(15)],
    }


def run_js(script, m):
    exe = shutil.which("node")
    if exe is None:
        pytest.skip("Node is required to verify the shipped browser management code")
    helpers = "let launchingTournamentBout=null;" + JS.split(
        "let launchingTournamentBout=null;", 1
    )[1].split("function earnedNextStartingCards(m){", 1)[0]
    prep = """
const elements={};
function node(tag,cls,text){
 const n={tag,className:cls||'',textContent:text||'',children:[],attributes:{},
 value:'',disabled:false,hidden:false,
 append(...items){this.children.push(...items)},
 replaceChildren(...items){this.children=[...items]},
 scrollIntoView(){}};
 return n;
}
function $(id){return elements[id]??=(node('div',id))}
function card(c,fn){return node('button','card',c.name)}
function displayCardName(name){return name}
function inspect(){}
function b11TachiaiPreview(m,g){return node('div','preview','Tachiai preview')}
const saved=[];
function managementSave(){saved.push(JSON.stringify(management))}
let management=JSON.parse(process.argv[1]);
let token=null,sessionSetup=null,game=null,actionJournal=[];
function activeTournamentBout(){return sessionSetup?.tournament_bout??null}
const requests=[];
async function api(path,body){
 requests.push({path,body});
 if(globalThis.failLaunch)throw new Error('Simulated server failure');
 return {token:'test-session',state:{finished:false}};
}
function render(state){game=state}
const document={querySelector(){return {scrollIntoView(){}}}};
"""
    r = subprocess.run(
        [exe, "-e", prep + helpers + "\n(async()=>{\n" + script + "\n})().catch(e=>{console.error(e);process.exit(1)});",
         json.dumps(m)],
        capture_output=True, text=True, check=False, timeout=15,
    )
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_all_nine_are_planned_before_the_first_bout():
    result = run_js("""
managementBoard();
const buttons=$('management-groups').children.map(group=>
 group.children.filter(c=>c.tag==='select').map(c=>c.disabled));
console.log(JSON.stringify({valid:allBoutCardsAssigned(management),
  startHidden:$('management-start').hidden,
  startDisabled:$('management-start').disabled,buttons}));
""", fixture())
    assert result == {
        "valid": True, "startHidden": False, "startDisabled": False,
        "buttons": [[False] * 3 for _ in range(3)],
    }


def test_completed_bout_one_is_frozen_but_bouts_two_and_three_swap():
    result = run_js("""
managementBoard();
const before=JSON.stringify(management.groups[0]);
const lockedAttempt=changeBoutAssignment(management,0,0,6);
const futureSwap=changeBoutAssignment(management,1,0,6);
managementBoard();
const disabled=$('management-groups').children.map(group=>
 group.children.filter(c=>c.tag==='select').map(c=>c.disabled));
console.log(JSON.stringify({lockedAttempt,futureSwap,before,groups:management.groups,
 disabled,valid:allBoutCardsAssigned(management),
 startHidden:$('management-start').hidden,
 lockedLabel:$('management-groups').children[0].children[0].textContent}));
""", fixture(results=1))
    assert result["lockedAttempt"] is False
    assert result["futureSwap"] is True
    assert result["groups"] == [[0, 1, 2], [6, 4, 5], [3, 7, 8]]
    assert result["disabled"] == [[True] * 3, [False] * 3, [False] * 3]
    assert result["valid"] is True
    assert result["startHidden"] is True
    assert "COMPLETED — LOCKED" in result["lockedLabel"]


def test_completed_bout_two_locks_while_third_remains_editable():
    result = run_js("""
managementBoard();
const changedPast=changeBoutAssignment(management,1,1,7);
const changedFuture=changeBoutAssignment(management,2,1,null);
managementBoard();
console.log(JSON.stringify({changedPast,changedFuture,groups:management.groups,
 locks:$('management-groups').children.map(group=>
 group.children.filter(c=>c.tag==='select')[0].disabled)}));
""", fixture(results=2, round=1))
    assert result == {
        "changedPast": False, "changedFuture": True,
        "groups": [[0, 1, 2], [3, 4, 5], [6, None, 8]],
        "locks": [True, True, False],
    }


def test_after_third_bout_all_nine_cards_remain_immutable():
    result = run_js("""
managementBoard();
const attempts=[0,1,2].map(i=>changeBoutAssignment(management,i,0,null));
console.log(JSON.stringify({attempts,groups:management.groups,
 startHidden:$('management-start').hidden,
 locks:$('management-groups').children.map(group=>
 group.children.filter(c=>c.tag==='select')[0].disabled)}));
""", fixture(results=3, round=2))
    assert result == {
        "attempts": [False, False, False], "groups": [[0, 1, 2], [3, 4, 5], [6, 7, 8]],
        "startHidden": True, "locks": [True, True, True],
    }


def test_old_save_restores_recorded_bout_cards_and_prevents_reuse():
    # The pre-fix browser let players move card 0 from finished Bout 1 to Bout 2.
    # The original three physical cards survive in result.assigned_cards.
    result = run_js("""
managementBoard();
console.log(JSON.stringify({groups:management.groups,locked:management.locked_bouts[0],
 valid:allBoutCardsAssigned(management),saves:saved.length}));
""", fixture(results=1, groups=[[3, 1, 2], [0, 4, 5], [6, 7, 8]]))
    assert result["groups"] == [[0, 1, 2], [None, 4, 5], [6, 7, 8]]
    assert result["locked"] == [0, 1, 2]
    assert result["valid"] is False
    assert result["saves"] >= 1


def test_already_started_bout_is_locked_even_before_its_result():
    result = run_js("""
managementBoard();
const attempted=changeBoutAssignment(management,0,0,6);
console.log(JSON.stringify({attempted,locked:allocationLockState(management,0),
 groups:management.groups,startHidden:$('management-start').hidden}));
""", fixture(locks={"0": [0, 1, 2]}))
    assert result == {
        "attempted": False, "locked": "started",
        "groups": [[0, 1, 2], [3, 4, 5], [6, 7, 8]],
        "startHidden": True,
    }


def test_next_block_starts_with_new_unlocked_nine_cards():
    result = run_js("""
managementBoard();
console.log(JSON.stringify({first:currentBlockStart(management),
 states:[0,1,2].map(i=>allocationLockState(management,i)),
 startHidden:$('management-start').hidden}));
""", fixture(round=3, locks={"0": [0, 1, 2], "1": [3, 4, 5], "2": [6, 7, 8]}))
    assert result == {"first": 3, "states": [None, None, None], "startHidden": False}


def test_accepted_bout_locks_cards_and_failed_launch_does_not():
    success = run_js("""
managementBoard();
await managementRound();
console.log(JSON.stringify({locked:management.locked_bouts[0],
 startHidden:$('management-start').hidden,
 saved:saved.length,token,setup:sessionSetup,requests:requests.length}));
""", fixture())
    assert success["locked"] == [0, 1, 2]
    assert success["startHidden"] is True
    assert success["saved"] >= 1
    assert success["token"] == "test-session"
    assert success["setup"]["tournament_bout"] == 0
    assert success["requests"] == 1

    failed = run_js("""
globalThis.failLaunch=true;
let error='';
try{await managementRound()}catch(e){error=e.message}
console.log(JSON.stringify({error,locked:management.locked_bouts[0]??null,
 next:launchingTournamentBout,hidden:$('management-start').hidden,
 disabled:$('management-start').disabled}));
""", fixture())
    assert failed["error"] == "Simulated server failure"
    assert failed["locked"] is None
    assert failed["next"] is None
    assert failed["hidden"] is False and failed["disabled"] is False


def test_incomplete_assignments_cannot_start_next_bout():
    result = run_js("""
let error='';
try{await managementRound()}catch(e){error=e.message}
managementBoard();
console.log(JSON.stringify({error,valid:allBoutCardsAssigned(management),
 disabled:$('management-start').disabled,requests:requests.length}));
""", fixture(groups=[[0, 1, 2], [3, None, 5], [6, 7, 8]]))
    assert "all nine distinct cards" in result["error"]
    assert result["valid"] is False
    assert result["disabled"] is True
    assert result["requests"] == 0


def test_same_named_cards_remain_individually_assignable():
    result = run_js("""
managementBoard();
const names=management.cards.map(c=>c.name);
const result=changeBoutAssignment(management,1,0,6);
console.log(JSON.stringify({names,result,groups:management.groups,valid:allBoutCardsAssigned(management)}));
""", fixture(results=1))
    assert result["names"][0] == result["names"][1]
    assert result["result"] is True
    assert result["valid"] is True
    assert result["groups"][0] == [0, 1, 2]


def test_public_heya_explains_lock_and_future_swapping():
    assert "Once a bout starts" in HTML
    assert "upcoming bouts only" in HTML
    assert ".management-group-locked" in CSS
    assert ".assignment-locked-note" in CSS
    assert "$('management-start').hidden=!atStart" in JS
    assert "if(!allBoutCardsAssigned(m))" in JS
    assert "m.locked_bouts[i]=committed" in JS
    assert "updateTournamentLeaders(m);managementSave();managementBoard()" in JS
