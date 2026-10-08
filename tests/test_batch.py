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
