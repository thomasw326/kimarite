from kimarite.setup import BoutConfig, FighterConfig
from kimarite.simulate import run_bout


def test_known_fujinokawa_tochinoshin_case_completes_autonomously():
    result = run_bout(
        BoutConfig(
            FighterConfig(
                "Fujinokawa",
                102,
                frozenset({7, 14, 15, 16, 29, 35, 43}),
                ranking=1,
            ),
            FighterConfig(
                "Tochinoshin",
                911132,
                frozenset({18, 19, 21, 28, 31, 32, 33}),
                ranking=2,
            ),
        ),
        max_turns=100,
    )

    assert result.completed, result.unsupported_reason
    assert result.state.winner is not None
    assert result.state.win_method is not None


def test_known_manual_fujinokawa_tochinoshin_line_has_same_winner():
    result = run_bout(
        BoutConfig(
            FighterConfig(
                "Fujinokawa",
                102,
                frozenset({7, 14, 15, 16, 29, 35, 43}),
                ranking=1,
            ),
            FighterConfig(
                "Tochinoshin",
                911132,
                frozenset({18, 19, 21, 28, 31, 32, 33}),
                ranking=2,
            ),
        ),
        max_turns=100,
    )

    assert result.completed, result.unsupported_reason
    assert result.state.winner is not None
    assert result.state.fighter(result.state.winner).wrestler.name == "Tochinoshin"
    assert result.state.win_method == "Yorikiri"
