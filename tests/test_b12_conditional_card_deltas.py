"""Synthetic bout records verify the six-delta reporting contract."""
import csv
import json
import subprocess
import sys
from pathlib import Path


def test_six_card_deltas(tmp_path):
    records = []
    # Card X included in A, absent in B. Opening assignments differ.
    # Two X-prepared bouts, two X-top-deck bouts, two neither.
    cases = [
        ("X", "Y", True, True),
        ("X", "Y", False, False),
        ("Y", "X", True, False),
        ("Y", "X", False, True),
        ("Y", "Z", True, True),
        ("Y", "Z", False, False),
    ]
    for i, (prepared, top, played, won) in enumerate(cases):
        def fighter(frm, deck, prep, top, plays):
            return dict(framework=frm, deck=deck, prepared_tachiai=prep,
                        top_deck=top, starting_kimarite="K", plays=plays,
                        seen_hand=[], held_end_turn=[], kept_at_turn_start={})
        delta = dict.fromkeys(("push_position", "momentum", "power", "foe_power",
                               "grip", "foe_grip", "hand", "draw_pile", "foe_draw_pile",
                               "discard", "foe_discard", "plays_remaining"), 0)
        records.append(dict(
            mode="max40", global_id=i, source_sha256="fixture", pair_id=i,
            repetition=0, framework_a="01", framework_b="02",
            error=None, winner_side="A" if won else "B", win_method="Power",
            win_source="power", winning_kimarite_origin=None, turns=1,
            fighters={"A": fighter("01", ["X", "X", "Y", "Z"], prepared, top,
                       [dict(card="X", origin="deck", delta=delta)] if played else []),
                      "B": fighter("02", ["Y", "Z"], "Y", "Z", [])},
            opening=dict(power_advantage_a=0, technique_advantage_a=0, spirit_advantage_a=0),
            temporary_outcomes=[]))
    src = tmp_path / "bouts_fixture.jsonl"
    src.write_text("\n".join(json.dumps(r) for r in records))
    out = tmp_path / "report"
    script = Path(__file__).resolve().parents[1] / "scripts" / "b12_60_report.py"
    subprocess.run([sys.executable, str(script), "--input-root", str(tmp_path),
                    "--output-dir", str(out), "--allow-partial"], check=True)
    with (out / "card_six_deltas.csv").open() as f:
        rows = list(csv.DictReader(f))
    row = next(r for r in rows if r["mode"] == "max40" and r["card"] == "X")
    assert float(row["played_delta_pp"]) == 33.333
    assert float(row["non_tachiai_played_delta_pp"]) == 0
    assert float(row["non_top_deck_played_delta_pp"]) == 100
    assert row["non_tachiai_played_positive_bouts"] == "2"
    assert row["non_tachiai_played_negative_bouts"] == "2"
    assert row["non_top_deck_played_positive_wins"] == "2"
    assert row["non_top_deck_played_negative_wins"] == "0"
    assert row["inclusion_positive_bouts"] == "6"  # duplicate copies do not double-count
    assert row["played_low_sample"] == "True"
    absent = next(r for r in rows if r["mode"] == "base28" and r["card"] == "X")
    assert absent["played_delta_pp"] == ""
