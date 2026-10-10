"""Playable archetype-vs-archetype human bout smoke tests."""
from kimarite.human_bout import HumanBout
from kimarite.styles_v5 import STYLES


def test_style_opponent_reaches_play_or_result():
    bout = HumanBout.new_styles("Mountain", "The Technician", seed=42, max_turns=20)
    assert bout.state.fighter_a.wrestler.name == "Mountain"
    assert bout.state.fighter_b.wrestler.name == "The Technician"
    assert bout.finished or bout.awaiting_human


def test_style_selection_is_reproducible():
    first = HumanBout.new_styles("Speed Demon", "Disruptor", seed=11)
    second = HumanBout.new_styles("Speed Demon", "Disruptor", seed=11)
    assert first.view() == second.view()


def test_fifteen_styles_are_available():
    assert len(STYLES) == 15
