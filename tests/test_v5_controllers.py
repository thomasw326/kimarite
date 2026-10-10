"""Controller integration: legacy modes retain results and per-side choice works."""
import pytest

from kimarite.controllers import controller_for_mode
from kimarite.models import Side
from kimarite.setup import BoutConfig, FighterConfig
from kimarite.simulate import run_bout


CONFIG = BoutConfig(
    FighterConfig("Fujinokawa", 102, ranking=1),
    FighterConfig("Tochinoshin", 911132, ranking=2),
)


@pytest.mark.parametrize("mode", ["tactical", "personality"])
def test_explicit_controller_pair_matches_legacy_mode(mode):
    before = run_bout(CONFIG, max_turns=8, ai_mode=mode)
    controller = controller_for_mode(mode)
    after = run_bout(
        CONFIG,
        max_turns=8,
        ai_mode=mode,
        controllers={Side.A: controller, Side.B: controller},
    )
    assert (after.completed, after.turns, after.state.winner, after.state.win_method) == (
        before.completed, before.turns, before.state.winner, before.state.win_method
    )
    assert after.state.card_plays == before.state.card_plays


def test_custom_controller_acts_for_its_own_side_only():
    seen = []

    def pass_turn(state, side, comparison):
        assert side is Side.A
        assert state.active_side is Side.A
        assert state.fighter(side).plays_remaining >= 0
        seen.append(state.turn_number)

    result = run_bout(CONFIG, max_turns=12, controllers={Side.A: pass_turn})
    assert seen
    assert result.turns <= 12
    assert all(n >= 1 for n in seen)


def test_unknown_legacy_mode_still_fails():
    with pytest.raises(ValueError, match="Unknown AI mode"):
        run_bout(CONFIG, ai_mode="unknown")
