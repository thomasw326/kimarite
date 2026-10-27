"""B11 tournament-completion UI contract, including old saved 15-bout runs."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_final_results_are_reopenable_from_existing_session_storage():
    js = (ROOT / "web/client.js").read_text()
    html = (ROOT / "web/index.html").read_text()
    assert "if(m.results.length===15)" in js
    assert "managementStatus()" in js
    assert "$('management-summary').hidden=m.results.length!==15" in js
    assert "if(management?.results.length===15){showTournamentFinal();return}" in js
    assert 'id="management-summary"' in html
    assert 'id="tournament-final"' in html


def test_final_results_show_five_rounds_and_all_bouts():
    js = (ROOT / "web/client.js").read_text()
    assert "for(let i=0;i<5;i++)" in js
    assert "m.results.slice(i*3,i*3+3)" in js
    assert "'Bout '+(i*3+k+1)" in js
    assert "' · '+(r.won?'WIN':'LOSS')" in js
    assert "tournamentFinalText(management)" in js
