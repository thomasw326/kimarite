"""Six-tournament year keeps per-tournament history across fresh 28-card drafts."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
JS = (WEB / "client.js").read_text(encoding="utf-8")
HTML = (WEB / "index.html").read_text(encoding="utf-8")


def run_helpers(expr):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is needed to execute browser campaign helpers")
    helper = "function yearHistory(m){" + JS.split("function yearHistory(m){", 1)[1].split(
        "function tournamentFinalText(m){", 1
    )[0]
    script = """
const elements={};const $=id=>elements[id]??={textContent:''};
""" + helper + expr
    result = subprocess.run([node, "-e", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_sumo_year_starts_at_tournament_one_without_old_saved_history():
    result = run_helpers("""
const m={human:'My Rikishi',results:[]};
showYearStatus(m);
console.log(JSON.stringify({history:yearHistory(m),score:$('year-record').textContent}));
""")
    assert result["history"] == []
    assert "Tournament 1 of 6" in result["score"]
    assert "Year record 0–0" in result["score"]


@pytest.mark.parametrize("wins", [0, 7, 15])
def test_completed_tournament_summary_records_15_bout_results(wins):
    result = run_helpers(f"""
const m={{human:'My Rikishi',results:Array.from({{length:15}},(_,i)=>({{
 won:i<{wins},opponent:'AI '+i,finish:'Oshidashi',turns:2
}}))}};
const t=tournamentSummary(m);
showYearStatus(m);
console.log(JSON.stringify({{summary:t,score:$('year-record').textContent}}));
""")
    assert result["summary"]["tournament"] == 1
    assert result["summary"]["wins"] == wins
    assert result["summary"]["losses"] == 15-wins
    assert len(result["summary"]["results"]) == 15
    assert f"Year record {wins}–{15-wins}" in result["score"]
    assert "1 tournament completed" in result["score"]


def test_sixth_tournament_completes_90_bout_year():
    result = run_helpers("""
const h=Array.from({length:5},(_,i)=>({tournament:i+1,wins:10,losses:5,results:[]}));
const m={tournament_history:h,results:Array.from({length:15},(_,i)=>({won:i<8,opponent:'AI'}))};
const summary=tournamentSummary(m);
showYearStatus(m);
console.log(JSON.stringify({summary,score:$('year-record').textContent,
 totalWins:h.reduce((n,t)=>n+t.wins,0)+summary.wins}));
""")
    assert result["summary"]["tournament"] == 6
    assert result["totalWins"] == 58
    assert "Tournament 6 of 6" in result["score"]
    assert "Year record 58–32" in result["score"]
    assert "Year complete" in result["score"]


def test_year_cannot_advance_to_seventh_and_draft_preserves_history():
    assert "if(previous&&yearHistory(previous).length>=5)" in JS
    assert "tournament_history=previous?[...yearHistory(previous),tournamentSummary(previous)]:[]" in JS
    assert "activeDraft={human,seed,world_seed:" in JS
    assert "created_stats:created,tournament_history,starting_cards:[...starting]" in JS
    assert "division_roster:division?.roster||null" in JS
    assert "tournament_history:d.tournament_history||[]" in JS
    assert "yearHistory(management).length>=5)return" in JS
    assert "$('management-new').hidden=m.results.length!==15||m.opening_mode==='classic'||!completedRewards(m)||yearHistory(m).length>=5" in JS
    assert "showYearStatus(d)" in JS
    assert "showYearStatus(management)" in JS


def test_year_progress_appears_in_heya_and_tournament_final():
    assert 'id="year-record" class="year-record" aria-live="polite"' in HTML
    assert 'id="tournament-year-record" class="year-record"' in HTML
    assert "$('tournament-year-record').textContent='Year record:" in JS
    assert "const history=[...yearHistory(m),tournamentSummary(m)]" in JS
    assert "Sumo year:" in JS
