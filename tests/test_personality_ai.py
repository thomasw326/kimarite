from itertools import permutations

import pytest

from kimarite.ai import AIPlay
from kimarite.effects import EffectContext
from kimarite.models import BoutState, Card, FighterState, Side, Stat, Wrestler
from kimarite.personality_ai import choose_personality_play
from kimarite.setup import BoutConfig, FighterConfig
from kimarite.simulate import run_bout
from kimarite.tachiai import compare_tachiai


@pytest.mark.parametrize("order", list(permutations(Stat)))
def test_all_six_priority_orders_select_their_primary(monkeypatch, order):
    blank = Card(9999, "Blank")
    a = Wrestler("A", 0, 0, 0, blank, blank, blank,
                 primary=order[0], secondary=order[1], tertiary=order[2])
    b = Wrestler("B", 0, 0, 0, blank, blank, blank)
    cards = [
        Card(1, "Power card", power=3),
        Card(2, "Technique card", technique=3),
        Card(3, "Spirit card", spirit=3),
    ]
    state = BoutState(FighterState(a, hand=cards), FighterState(b))
    scores = (16.0, 20.0, 24.0)

    monkeypatch.setattr(
        "kimarite.personality_ai.candidate_plays",
        lambda *_: [AIPlay(card, EffectContext(), score)
                    for card, score in zip(cards, scores)],
    )
    monkeypatch.setattr("kimarite.personality_ai.score_state", lambda *_: 0.0)

    selected = choose_personality_play(state, Side.A, compare_tachiai(a, b))
    assert selected is not None
    assert selected.card.orbs(order[0]) == 3


def test_immediate_win_overrides_personality(monkeypatch):
    blank = Card(9999, "Blank")
    a = Wrestler("A", 0, 0, 0, blank, blank, blank)
    b = Wrestler("B", 0, 0, 0, blank, blank, blank)
    cards = [Card(1, "Preferred", power=3), Card(2, "Win", technique=3)]
    state = BoutState(FighterState(a, hand=cards), FighterState(b))
    monkeypatch.setattr(
        "kimarite.personality_ai.candidate_plays",
        lambda *_: [AIPlay(cards[0], EffectContext(), 10.0),
                    AIPlay(cards[1], EffectContext(), 1_000_000.0)],
    )
    monkeypatch.setattr("kimarite.personality_ai.score_state", lambda *_: 0.0)
    assert choose_personality_play(state, Side.A, compare_tachiai(a, b)).card == cards[1]


def test_personality_mode_is_available_without_replacing_baseline():
    config = BoutConfig(FighterConfig("Fujinokawa", 102),
                        FighterConfig("Tochinoshin", 911132))
    assert run_bout(config, max_turns=2, ai_mode="tactical").turns <= 2
    assert run_bout(config, max_turns=2, ai_mode="personality").turns <= 2
    with pytest.raises(ValueError):
        run_bout(config, ai_mode="unknown")
