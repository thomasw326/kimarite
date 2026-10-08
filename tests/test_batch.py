from kimarite.batch import run_series, summarize_series


def test_batch_series_records_winner_method_and_cards():
    records = run_series(
        "Fujinokawa",
        "Tochinoshin",
        [(102, 911132)],
        exclusions_a=frozenset({7, 14, 15, 16, 29, 35, 43}),
        exclusions_b=frozenset({18, 19, 21, 28, 31, 32, 33}),
    )

    assert len(records) == 1
    record = records[0]
    assert record.completed
    assert record.winner in {"Fujinokawa", "Tochinoshin"}
    assert record.win_method is not None

    summary = summarize_series(records)
    assert summary.completed_bouts == 1
    assert sum(summary.wins.values()) == 1
    assert summary.average_turns >= 0


def test_round_robin_balances_both_orientations():
    from kimarite.batch import run_round_robin, standings

    records = run_round_robin(
        ["Fujinokawa", "Tochinoshin", "Daieisho"],
        bouts_per_orientation=1,
        max_turns=100,
        seed_start=50,
    )

    # Three unordered pairings, two orientations each.
    assert len(records) == 6

    table = standings(records)
    assert {row.wrestler for row in table} == {
        "Fujinokawa",
        "Tochinoshin",
        "Daieisho",
    }
    assert all(row.bouts == 4 for row in table)
