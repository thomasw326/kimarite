"""V5 shared-controller integration tests."""
from kimarite.models import Side
from kimarite.setup import BoutConfig, FighterConfig
from kimarite.simulate import run_bout


CONFIG = BoutConfig(
    FighterConfig("Fujinokawa", 102, ranking=1),
    FighterConfig("Tochinoshin", 911132, ranking=2),
)


def test_explicit_ai_controllers_match_legacy_simulation():
    from kimarite.controllers import ai_controller

    before = run_bout(CONFIG, max_turns=12)
    after = run_bout(
        CONFIG,
        max_turns=12,
        controllers={Side.A: ai_controller, Side.B: ai_controller},
    )
    assert (after.completed, after.turns, after.state.winner, after.state.win_method) == (
        before.completed, before.turns, before.state.winner, before.state.win_method
    )
    assert after.state.card_plays == before.state.card_plays


def test_custom_controller_receives_only_its_own_turns():
    seen = []

    def pass_turn(state, side, comparison):
        assert side is Side.A
        assert state.active_side is Side.A
        assert state.fighter(side).plays_remaining == 2
        seen.append(state.turn_number)

    result = run_bout(
        CONFIG,
        max_turns=6,
        controllers={Side.A: pass_turn},
    )
    assert seen  # A was controlled without changing the opponent's AI.
    assert all(n >= 1 for n in seen)
    assert result.turns <= 6
