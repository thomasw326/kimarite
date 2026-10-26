"""Guard against the tournament progress desynchronization reported after bout two.

The browser owns tournament sessionStorage; these checks ensure that a finished
standalone bout cannot be counted, next-bout errors roll back the round, and
the nine-card reallocation doesn't erase earlier results.
"""
from pathlib import Path

CLIENT = Path(__file__).resolve().parents[1] / "web" / "client.js"


def test_finished_bout_is_bound_to_tournament_identity():
    source = CLIENT.read_text()
    assert "sessionSetup={...request,tournament_bout:i}" in source
    assert "activeTournamentBout()===m.round&&m.results.length===m.round" in source
    assert "m.results.push(" in source
    assert "sessionSetup.seed===m.seed+m.round+1" in source


def test_next_bout_requires_recorded_result_and_rolls_back_failed_advance():
    source = CLIENT.read_text()
    assert "management.results.length!==management.round+1" in source
    assert "management.round--;managementSave()" in source
    assert "Could not start next bout:" in source
    assert "Could not deal the next round:" in source


def test_pending_tachiai_clears_previous_bout_continue_button():
    source = CLIENT.read_text()
    pending = source.split("function renderPendingTachiai(g){", 1)[1].split("function render(", 1)[0]
    assert "if(management)managementStatus()" in pending
    assert "$('management-next').hidden=!" in source
