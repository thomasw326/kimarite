import pytest
from kimarite.style_round_robin_v5 import run_round_robin


def test_zero_repetitions():
    with pytest.raises(ValueError):
        run_round_robin(repetitions=0)


def test_pair_legs_share_base_seed(monkeypatch):
    """Both seat orders must reuse a seed, without claiming identical decks."""
    import kimarite.style_round_robin_v5 as rr
    from types import SimpleNamespace
    from kimarite.models import Side

    observed = []
    def fake_bout(a, b, *, seed, max_turns):
        observed.append((a, b, seed))
        state = SimpleNamespace(
            card_plays=[], winner=Side.A, win_method="Oshidashi"
        )
        return SimpleNamespace(completed=True, turns=1, state=state)

    monkeypatch.setattr(rr, "run_style_bout", fake_bout)
    result = rr.run_round_robin(repetitions=1, seed=123, max_turns=5)
    assert result["completed"] == 210
    assert len(observed) == 210
    for i in range(0, len(observed), 2):
        a, b, seed1 = observed[i]
        c, d, seed2 = observed[i + 1]
        assert (a, b) == (d, c)
        assert seed1 == seed2
