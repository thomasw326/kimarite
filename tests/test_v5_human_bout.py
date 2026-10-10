"""V5 playable session: manual card access, actions, and AI progression."""
from copy import deepcopy

import pytest

from kimarite.effects import ChoiceRequired, IllegalPlay
from kimarite.human_bout import HumanBout
from kimarite.models import Side
from kimarite.setup import BoutConfig, FighterConfig


CONFIG = BoutConfig(
    FighterConfig("Fujinokawa", 102, ranking=1),
    FighterConfig("Fujinokawa", 911132, ranking=2),
)


def selected_bout(*, max_turns=12, side=Side.A):
    bout = HumanBout.new(CONFIG, human_side=side, max_turns=max_turns)
    if bout.pending_selection:
        pending = bout.pending_selection
        bout.choose_cards(list(range(pending.keep)))
    return bout


def test_selection_pauses_without_mutating_authoritative_turn():
    bout = HumanBout.new(CONFIG, human_side=Side.A, max_turns=12)
    assert bout.awaiting_human
    assert bout.pending_selection is not None
    assert bout.state.turn_number == 0
    assert not bout.actions()
    before = deepcopy(bout.state)
    with pytest.raises(IllegalPlay):
        bout.end_turn()
    with pytest.raises(IllegalPlay):
        bout.play(0)
    with pytest.raises(IllegalPlay):
        bout.choose_cards([999] * bout.pending_selection.keep)
    assert bout.state == before
    indices = list(range(bout.pending_selection.keep))
    expected = [bout.pending_selection.options[i].name for i in indices]
    bout.choose_cards(indices)
    assert bout.pending_selection is None
    assert bout.state.turn_number == 1
    assert [c.name for c in bout.state.fighter_a.hand][-len(expected):] == expected if expected else True


def test_session_reaches_human_and_allows_pass():
    bout = selected_bout()
    assert bout.awaiting_human
    assert bout.state.active_side is Side.A
    first_turn = bout.state.turn_number
    bout.end_turn()
    assert bout.state.turn_number >= first_turn + 1 or bout.finished


def test_ai_opener_advances_to_human():
    bout = HumanBout.new(CONFIG, human_side=Side.B, max_turns=12)
    if not bout.finished:
        assert bout.awaiting_human
        if bout.pending_kimarite_search is not None:
            # AI can pause its own turn for an opponent-owned search decision.
            assert bout.state.active_side is Side.A
            eligible = [i for i, c in enumerate(bout.state.fighter_b.draw_pile) if c.is_kimarite]
            bout.choose_kimarite_search(eligible[0])
        if not bout.finished:
            assert bout.state.active_side is Side.B
            assert bout.pending_selection is not None


def test_human_play_is_incremental():
    bout = selected_bout()
    if bout.actions():
        selected = bout.actions()[0]
        try:
            bout.play(selected.hand_index)
        except ChoiceRequired:
            assert bout.awaiting_human
        else:
            assert bout.awaiting_human or bout.finished
            assert bout.state.card_plays[-1][0] is Side.A


def test_session_rejects_actions_after_human_pass():
    bout = selected_bout(max_turns=1)
    assert bout.awaiting_human
    bout.end_turn()
    assert bout.finished
    with pytest.raises(IllegalPlay):
        bout.play(0)


def test_invalid_ai_mode_is_rejected():
    with pytest.raises(ValueError, match="Unknown AI mode"):
        HumanBout.new(CONFIG, ai_mode="invalid")
