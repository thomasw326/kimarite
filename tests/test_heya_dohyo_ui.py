"""Release UI: Heya management and Dohyō combat must be distinct phases."""
from pathlib import Path
import json
import shutil
import subprocess

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
HTML = (WEB / "index.html").read_text(encoding="utf-8")
CSS = (WEB / "style.css").read_text(encoding="utf-8")
JS = (WEB / "client.js").read_text(encoding="utf-8")


def run_browser_helpers(script):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node not available on this developer machine")
    part = JS.split("function setGameLocation(location){", 1)[1].split(
        "async function api(path,body)", 1
    )[0]
    functions = "function setGameLocation(location){" + part
    prefix = """
const elements={};
const $=id=>(elements[id]??=( {hidden:false,textContent:'',open:false,
    close(){this.open=false} } ));
const data=new Map();
const sessionStorage={
    getItem:key=>data.has(key)?data.get(key):null,
    setItem:(key,value)=>data.set(key,value)
};
let scrolls=0;
const window={scrollTo(){scrolls++}};
const document={body:{dataset:{phase:'heya'}}};
let management=null,sessionSetup=null,game=null;
function managementStatus(){}
function completedBlock(){return false}
function unresolvedRewards(){return []}
function showTournamentFinal(){}
function openBlockRewards(){return false}
"""
    result = subprocess.run(
        [node, "-e", prefix + functions + "\n" + script],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_heya_and_dohyo_have_separate_nonoverlapping_content():
    heya = HTML.index('id="heya-view"')
    dohyo = HTML.index('id="dohyo-view"')
    dialogs = HTML.index('<dialog id="discard-dialog"')
    assert heya < dohyo < dialogs
    assert 'id="dohyo-view" class="phase-view dohyo-view" aria-label="Dohyō combat" hidden' in HTML
    for name in ["management-deal", "b11-draft", "management-board", "management-rewards"]:
        assert heya < HTML.index(f'id="{name}"') < dohyo
    for name in ["return-heya", "tracks", "opening", "score", "history", "choices", "hand", "notice"]:
        assert dohyo < HTML.index(f'id="{name}"') < dialogs
    # Dialogs stay outside both views so they remain accessible from either location.
    assert dialogs < HTML.index('id="tournament-final"')
    assert '<button id="result-next" type="button">Return to Heya</button>' in HTML


def test_location_visual_identity_and_safe_hidden_handling():
    assert ".phase-view[hidden]{display:none!important}" in CSS
    assert 'body[data-phase="heya"] .bout-hud{display:none!important}' in CSS
    assert 'body[data-phase="dohyo"]' in CSS
    assert 'body[data-phase="heya"]' in CSS
    assert '#return-heya[hidden]{display:none!important}' in CSS


def test_location_switch_updates_views_and_scrolls_only_on_change():
    result = run_browser_helpers("""
setGameLocation('dohyo');
setGameLocation('dohyo');
const a={
    heyaHidden:$('heya-view').hidden,
    dohyoHidden:$('dohyo-view').hidden,
    heading:$('phase-heading').textContent,
    phase:document.body.dataset.phase,
    saved:sessionStorage.getItem('kimarite_ui_phase'),
    scrolls
};
setGameLocation('heya');
console.log(JSON.stringify({a,heya:$('heya-view').hidden,
    dohyo:$('dohyo-view').hidden,phase:document.body.dataset.phase,scrolls}));
""")
    assert result["a"] == {
        "heyaHidden": True, "dohyoHidden": False,
        "heading": "Dohyō · The Ring",
        "phase": "dohyo", "saved": "dohyo", "scrolls": 1,
    }
    assert (result["heya"], result["dohyo"], result["phase"], result["scrolls"]) == (
        False, True, "heya", 2,
    )


def test_finished_return_does_not_advance_to_next_bout():
    handler = JS.split("async function returnToHeya(){", 1)[1].split(
        "$('result-next').onclick=returnToHeya;", 1
    )[0]
    assert "next.click()" not in handler
    assert "setGameLocation('heya')" in handler
    assert "if(!game?.finished||resolvingB12Matchday)return;" in handler
    result = run_browser_helpers(
        "let resolvingB12Matchday=false;\n"
        "function isB12Campaign(){return false}\n"
        "function managementBoard(){}\n"
        "async function returnToHeya(){" + handler + "\n"
        + """
(async()=>{
  game={finished:false};setGameLocation('dohyo');
  await returnToHeya();
  const activePhase=document.body.dataset.phase;
  game={finished:true};await returnToHeya();
  console.log(JSON.stringify({activePhase,finishedPhase:document.body.dataset.phase,
      backHidden:$('return-heya').hidden,saved:sessionStorage.getItem('kimarite_ui_phase')}));
})().catch(e=>{console.error(e);process.exit(1)});
"""
    )
    assert result == {
        "activePhase": "dohyo", "finishedPhase": "heya",
        "backHidden": True, "saved": "heya",
    }


def test_completed_bout_stays_in_heya_after_reload():
    result = run_browser_helpers("""
sessionStorage.setItem('kimarite_ui_phase','heya');
sessionStorage.setItem('kimarite_management',JSON.stringify({round:2,results:[{},{},{}]}));
sessionSetup={tournament_bout:2};
const completed=returnedToHeyaAfterBout({finished:true});
const active=returnedToHeyaAfterBout({finished:false});
sessionSetup={tournament_bout:1};
const different=returnedToHeyaAfterBout({finished:true});
console.log(JSON.stringify({completed,active,different}));
""")
    assert result == {"completed": True, "active": False, "different": False}


def test_live_tachiai_always_enters_dohyo_and_keeps_opponent_hidden():
    assert "function renderPendingTachiai(g){\n updateDohyoPosition(g);\n setGameLocation('dohyo');" in JS
    assert "Your opponent’s Tachiai cards remain hidden until you commit." in JS
    assert "if(g.finished&&!alreadyInHeya){" in JS
    assert "showBoutResult(g);" in JS
    assert "startB12MatchdayPrefetch(g);" in JS
    assert JS.index("showBoutResult(g);") < JS.index("startB12MatchdayPrefetch(g);")
    assert "$('result-next').onclick=returnToHeya;" in JS
