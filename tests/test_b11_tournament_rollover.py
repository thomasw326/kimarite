"""B11 next-tournament starters are earned duplicate picks, not old defaults.

Evaluate the actual pure JavaScript rollover helper with Node when available.
The source contract check runs even on developer machines without Node.
"""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from kimarite.b11_player_draft import STARTERS, options_for, validate_draft

CLIENT = Path(__file__).resolve().parents[1] / "web" / "client.js"


def completed_first_draft(seed=12341):
    starting = list(STARTERS)
    picks = []
    while len(starting) + len(picks) < 28:
        picks.append(options_for(starting, picks, seed)[0])
    assert len(validate_draft(starting, picks, seed)) == 28
    return starting, picks


def rollover_helper():
    source = CLIENT.read_text(encoding="utf-8")
    start = source.index("function earnedNextStartingCards(m){")
    end = source.index("const B11_STARTER_SUITE=", start)
    return source[start:end]


def evaluate_rollover(management):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is needed to execute the browser rollover helper")
    script = (
        rollover_helper()
        + "\nconsole.log(JSON.stringify("
        + "earnedNextStartingCards(JSON.parse(process.argv[1]))));"
    )
    return subprocess.run(
        [node, "-e", script, json.dumps(management)],
        capture_output=True, text=True, check=False,
    )


@pytest.mark.parametrize("indices", [
    [],
    [0],
    [4, 10],
    [11, 0, 27, 3, 17, 5, 19, 9, 23, 1, 15, 8],
])
def test_earned_duplicates_form_exact_next_starters(indices):
    starting, picks = completed_first_draft()
    full_deck = starting + picks
    management = {
        "starting_cards": starting,
        "draft_picks": picks,
        "duplicated_indices": indices,
    }
    result = evaluate_rollover(management)
    assert result.returncode == 0, result.stderr
    inherited = json.loads(result.stdout)
    assert inherited == [full_deck[i] for i in indices]
    # Zero rewards means zero inherited cards, never the eight defaults.
    assert len(inherited) == len(indices)
    if len(indices) == 12:
        assert len(inherited) + 16 == 28


def test_rollover_preserves_two_physical_copies_of_same_name():
    starting, picks = completed_first_draft()
    starting[1] = starting[0]
    result = evaluate_rollover({
        "starting_cards": starting,
        "draft_picks": picks,
        "duplicated_indices": [1, 0],
    })
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [starting[0], starting[0]]


@pytest.mark.parametrize("indices", [[0, 0], list(range(13)), [-1], [28], [True]])
def test_rollover_rejects_invalid_or_repeated_physical_indices(indices):
    starting, picks = completed_first_draft()
    result = evaluate_rollover({
        "starting_cards": starting,
        "draft_picks": picks,
        "duplicated_indices": indices,
    })
    assert result.returncode != 0


def test_new_tournament_button_persists_replacements_before_new_draft():
    source = CLIENT.read_text(encoding="utf-8")
    assert "management.next_starting_cards=earnedNextStartingCards(management)" in source
    assert (
        "const starting=previous?"
        "(previous.next_starting_cards??earnedNextStartingCards(previous))"
        ":B11_STARTER_SUITE;"
    ) in source
    assert "management.results.length!==15||!completedRewards(management)" in source
    assert "managementSave();" in source
    assert "starting_cards:[...starting],picks:[]" in source
    assert "starting_cards:d.starting_cards,picks:d.picks" in source
    # A zero-reward [] must not become the default eight starter cards.
    assert "previous?.next_starting_cards||B11_STARTER_SUITE" not in source
