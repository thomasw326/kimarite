"""B11 opt-in multi-card Tachiai must not double-apply universal Spirit Push."""
from kimarite.catalog import card_by_name
from kimarite.models import BoutState, Card, FighterState, Side, Wrestler
from kimarite.b11_player_tachiai import compare_player_tachiai
from kimarite.tachiai_effects import resolve_prepared_tachiai


def test_two_shoves_apply_two_card_pushes_but_one_spirit_comparison():
    blank = Card(90001, "Blank")
    shove = card_by_name("Shove")
    human = Wrestler("Human", 0, 0, 4, blank, blank, blank)
    ai = Wrestler("AI", 0, 0, 0, blank, blank, blank)
    state = BoutState(FighterState(human), FighterState(ai))
    comparison = compare_player_tachiai(human, ai, [shove, shove])
    resolve_prepared_tachiai(state, comparison, committed_cards={Side.A: (shove, shove)})
    # +4 Spirit means 2 comparison Push once, plus 2 Shove Push.
    assert state.position == 3
    assert state.winner is Side.A
    assert state.win_method == "Shove"


def test_zero_commits_still_resolves_ai_prepared_card():
    blank = Card(90002, "Blank")
    shove = card_by_name("Shove")
    human = Wrestler("Human", 0, 0, 0, blank, blank, blank)
    ai = Wrestler("AI", 0, 0, 0, blank, shove, blank)
    state = BoutState(FighterState(human), FighterState(ai))
    comparison = compare_player_tachiai(human, ai, [])
    resolve_prepared_tachiai(state, comparison, committed_cards={Side.A: ()})
    assert state.position == -1
    assert not state.fighter_a.discard_pile
