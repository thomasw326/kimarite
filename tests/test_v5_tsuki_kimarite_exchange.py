"""Exchange effects of Tsukidashi and Tsukitaoshi Kimarite."""
import pytest

from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext
from kimarite.kimarite import kimarite_is_satisfied
from kimarite.kimarite_effects import resolve_kimarite_play_effect
from kimarite.models import BoutState, Card, FighterState, Side, Wrestler
from kimarite.playing import play_card


def _bout(position=0, momentum=0):
    tsukidashi = card_by_name("Tsukidashi")
    blank = Card(98011, "Test Blank")
    w = Wrestler("A", 2, 2, 2, tsukidashi, blank, blank)
    return BoutState(
        FighterState(w, draw_pile=[blank, blank], plays_remaining=1),
        FighterState(w, draw_pile=[blank]),
        position=position, momentum=momentum,
    )


@pytest.mark.parametrize("played_this_turn,expected_push", [
    (0, 0), (1, 0), (2, 0), (3, 1), (4, 1),
])
def test_tsukidashi_push_requires_third_or_later_card(played_this_turn, expected_push):
    # Negative Position is intentionally allowed: the old +1 requirement is gone.
    state = _bout(position=-1, momentum=0)
    state.fighter_a.cards_played_this_turn = played_this_turn
    resolve_kimarite_play_effect(state, Side.A, card_by_name("Tsukidashi"), EffectContext())
    assert state.position == -1 + expected_push
    assert not state.fighter_a.hand
    assert len(state.fighter_a.draw_pile) == 2
    assert state.fighter_a.plays_remaining == 1
    assert state.momentum == 0


@pytest.mark.parametrize("prior_plays,expected_position", [
    (0, 0), (1, 0), (2, 1), (3, 1),
])
def test_tsukidashi_itself_counts_toward_third_card(prior_plays, expected_position):
    state = _bout()
    tsukidashi = card_by_name("Tsukidashi")
    state.fighter_a.hand.append(tsukidashi)
    state.fighter_a.cards_played_this_turn = prior_plays
    play_card(state, Side.A, tsukidashi)
    assert state.fighter_a.cards_played_this_turn == prior_plays + 1
    assert state.position == expected_position
    assert state.fighter_a.plays_remaining == 0
    assert len(state.fighter_a.draw_pile) == 2
    assert not state.fighter_a.hand
    assert state.winner is None


def test_tsukidashi_third_play_can_push_to_four_without_ringout():
    state = _bout(position=3)
    # This invokes the effect directly; the normal play path would count
    # Tsukidashi itself before reaching this point.
    state.fighter_a.cards_played_this_turn = 3
    resolve_kimarite_play_effect(state, Side.A, card_by_name("Tsukidashi"), EffectContext())
    assert state.position == 4
    assert state.winner is None


def test_tsukidashi_win_condition_unchanged():
    state = _bout(position=3)
    card = card_by_name("Tsukidashi")
    state.fighter_a.cards_played_this_turn = 2
    assert not kimarite_is_satisfied(state, Side.A, card)
    state.fighter_a.cards_played_this_turn = 3
    assert kimarite_is_satisfied(state, Side.A, card)
    state.position = 2
    assert not kimarite_is_satisfied(state, Side.A, card)


def test_tsukitaoshi_exchange_bonus_does_not_require_momentum():
    state = _bout(momentum=-1)
    resolve_kimarite_play_effect(state, Side.A, card_by_name("Tsukitaoshi"), EffectContext())
    assert state.fighter_a.plays_remaining == 2
    assert len(state.fighter_a.draw_pile) == 1
    assert len(state.fighter_a.hand) == 0
    assert len(state.fighter_a.discard_pile) == 1
