"""V5 full-bout integration smoke tests."""
from kimarite.style_simulate_v5 import run_style_bout


def test_style_head_to_head():
    result = run_style_bout("Mountain", "The Technician", seed=73, max_turns=18)
    assert result.turns <= 18
    assert result.state.fighter_a.wrestler.name == "Mountain"
    assert result.state.fighter_b.wrestler.name == "The Technician"
    assert result.completed or result.unsupported_reason


def test_style_bout_is_seeded():
    a = run_style_bout("Speed Demon", "Disruptor", seed=5, max_turns=20)
    b = run_style_bout("Speed Demon", "Disruptor", seed=5, max_turns=20)
    assert (a.turns, a.state.winner, a.state.card_plays) == (
        b.turns, b.state.winner, b.state.card_plays
    )
