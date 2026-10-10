"""Human-vs-AI turns use the same Tachiai, card, and end-turn engine."""
import pytest

from kimarite.effects import IllegalPlay
from kimarite.human_bout import HumanBout
from kimarite.models import Side
from kimarite.setup import BoutConfig, FighterConfig


CONFIG = BoutConfig(
    FighterConfig("Fujinokawa", 102, ranking=1),
    FighterConfig("Fujinokawa", 911132, ranking=2),
)


def test_session_reaches_human_and_allows_pass():
    bout = HumanBout.new(CONFIG, human_side=Side.A, max_turns=12)
    assert bout.awaiting_human
    assert bout.state.active_side is Side.A
    first_turn = bout.state.turn_number
    assert bout.view().side is Side.A
    bout.end_turn()
    assert bout.state.turn_number >= first_turn + 1 or bout.finished


def test_ai_opener_advances_to_human():
    bout = HumanBout.new(CONFIG, human_side=Side.B, max_turns=12)
    if not bout.finished:
        assert bout.awaiting_human
        assert bout.state.active_side is Side.B


def test_human_play_is_incremental():
    bout = HumanBout.new(CONFIG, human_side=Side.A, max_turns=12)
    if bout.actions():
        selected = bout.actions()[0]
        try:
            bout.play(selected.hand_index)
        except Exception as exc:
            # Some cards need a context-sensitive effect choice.
            from kimarite.effects import ChoiceRequired
            assert isinstance(exc, ChoiceRequired)
            assert bout.awaiting_human
        else:
            assert bout.awaiting_human or bout.finished
            assert bout.state.card_plays[-1][0] is Side.A


def test_session_rejects_actions_after_human_pass():
    bout = HumanBout.new(CONFIG, human_side=Side.A, max_turns=1)
    assert bout.awaiting_human
    bout.end_turn()
    assert bout.finished
    with pytest.raises(IllegalPlay):
        bout.play(0)


def test_invalid_ai_mode_is_rejected():
    with pytest.raises(ValueError, match="Unknown AI mode"):
        HumanBout.new(CONFIG, ai_mode="invalid")
