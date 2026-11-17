"""Selected-card Tachiai preview is local-only and never guesses hidden opponent orbs."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest


CLIENT = (Path(__file__).resolve().parents[1] / "web" / "client.js").read_text(encoding="utf-8")


def evaluate_preview():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node required for browser preview helper")
    start = CLIENT.index("function b11PreviewTotals(cards){")
    end = CLIENT.index("function b11TachiaiPreview(m,group){", start)
    helper = CLIENT[start:end]
    script = helper + """
const cards=[
 {power:2,technique:0,spirit:1},
 {power:0,technique:3,spirit:0},
 {power:1,technique:1,spirit:2}
];
const base={power:2,technique:1,spirit:0};
const indices=[[],[0],[0,2],[0,1,2]];
console.log(JSON.stringify(indices.map(ids=>
 b11CommittedTachiaiTotals(cards,new Set(ids),base))));
"""
    result = subprocess.run([node, "-e", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_committed_only_orbs_and_baseline_are_correct_for_zero_to_three_cards():
    assert evaluate_preview() == [
        [3, 2, 1],      # No commitment: the player's base 2/1/0 plus one each.
        [5, 2, 2],      # First card only; the other two remain in Exchange.
        [6, 3, 4],      # First and third cards.
        [6, 6, 4],      # All three cards committed.
    ]


def test_live_pending_choice_refreshes_preview_without_revealing_opponent():
    start = CLIENT.index("function renderPendingTachiai(g){")
    end = CLIENT.index("let lastPresentedResult=null;", start)
    source = CLIENT[start:end]
    assert "b11CommittedTachiaiTotals(g.tachiai_choice.cards,picked,base)" in source
    assert "const base=sessionSetup?.created_stats||b11PreviewBase(g.human.name)" in source
    assert "refreshPreview()" in source
    assert "refreshPreview();" in source
    assert "Opponent totals stay hidden until you confirm." in source
    assert "commit_tachiai" in source
    assert "g.opening" not in source
    assert "g.opponent.opening" not in source
