"""Approved opening Power restoration and Headlong Charge choice reporting."""
from kimarite.catalog import card_by_name
from kimarite.models import Card
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.tachiai import compare_tachiai
from kimarite.tachiai_effects import resolve_prepared_tachiai
from kimarite.turns import apply_initial_power


def _bout(prepared: str):
    k = card_by_name("Oshidashi")
    t = card_by_name(prepared)
    blank = Card(90059, "Test Blank")
    a = Wrestler("A", 2, 2, 2, k, t, blank)
    b = Wrestler("B", 2, 2, 2, k, blank, blank)
    state = BoutState(
        FighterState(a, draw_pile=[blank, blank, blank, t], kimarite_zone=[k]),
        FighterState(b, draw_pile=[blank, blank, blank], kimarite_zone=[k]),
    )
    comparison = compare_tachiai(a, b)
    apply_initial_power(state, comparison)
    return state, comparison


def test_defensive_cards_restore_two_tachiai_power():
    for name in ("Hold Position", "Immovable"):
        state, comparison = _bout(name)
        starting_power = state.fighter_a.power
        resolve_prepared_tachiai(state, comparison)
        assert state.fighter_a.power == starting_power + 2


def test_headlong_decline_grants_no_bonus_and_discards_prepared_card():
    state, comparison = _bout("Headlong Charge")
    assert (card_by_name("Headlong Charge").power,
            card_by_name("Headlong Charge").technique,
            card_by_name("Headlong Charge").spirit) == (0, 0, 3)
    power = state.fighter_a.power
    resolve_prepared_tachiai(state, comparison, sacrifice_choices={Side.A: None})
    assert state.fighter_a.power == power
    assert state.headlong_decisions == [(Side.A, "Tachiai", "decline", None)]
    assert "Headlong Charge" not in [c.name for c in state.fighter_a.draw_pile]
    assert "Headlong Charge" in [c.name for c in state.fighter_a.discard_pile]
    assert len(state.fighter_a.draw_pile) == 3


def test_headlong_sacrifice_grants_momentum_and_push_only():
    state, comparison = _bout("Headlong Charge")
    power = state.fighter_a.power
    resolve_prepared_tachiai(state, comparison, sacrifice_choices={Side.A: 0})
    assert state.fighter_a.power == power
    assert state.headlong_decisions == [(Side.A, "Tachiai", "sacrifice", "Oshidashi")]
    assert not state.fighter_a.kimarite_zone
    assert "Oshidashi" in [c.name for c in state.fighter_a.discard_pile]
    # The sacrifice adds +1 Momentum and +1 Push to the standard opening.
    assert state.momentum == 1
    assert len(state.fighter_a.draw_pile) == 3
    assert state.position == 2


def test_headlong_bonus_is_blocked_by_opening_power():
    state, comparison = _bout("Headlong Charge")
    state.fighter_b.power = state.fighter_a.power + 4
    resolve_prepared_tachiai(state, comparison, sacrifice_choices={Side.A: 0})
    assert state.position == 0
    assert state.momentum == 1


def test_headlong_exchange_does_not_mill():
    from kimarite.playing import play_card
    from kimarite.effects import EffectContext
    state, comparison = _bout("Headlong Charge")
    charge = card_by_name("Headlong Charge")
    state.fighter_a.hand = [charge]
    before = list(state.fighter_a.draw_pile)
    play_card(state, Side.A, charge, context=EffectContext(choices={"sacrifice_kimarite": 0}))
    assert state.fighter_a.draw_pile == before
    assert state.position == 1
    assert state.momentum == 1


def test_read_the_move_printed_orbs():
    card = card_by_name("Read the Move")
    assert (card.power, card.technique, card.spirit) == (0, 1, 2)


def test_harite_tachiai_preserves_opponent_hand():
    state, comparison = _bout("Harite")
    held = Card(95001, "Held")
    state.fighter_b.hand = [held]
    power = state.fighter_b.power
    before = list(state.fighter_b.draw_pile)
    resolve_prepared_tachiai(state, comparison)
    assert state.fighter_b.hand == [held]
    assert state.fighter_b.power == power - 1
    # Opposing prepared ordinary card returns to the bottom after opening.
    assert state.fighter_b.draw_pile == before[2:] + [state.fighter_b.wrestler.prepared_tachiai_card]
    assert state.fighter_b.discard_pile == before[:2]


def test_harite_exchange_still_discards_hand_and_mills():
    from kimarite.playing import play_card
    state, comparison = _bout("Harite")
    card = card_by_name("Harite")
    held = Card(95002, "Held")
    state.fighter_a.hand = [card]
    state.fighter_b.hand = [held]
    power = state.fighter_b.power
    before = list(state.fighter_b.draw_pile)
    play_card(state, Side.A, card)
    assert not state.fighter_b.hand
    assert state.fighter_b.power == power - 1
    assert state.fighter_b.draw_pile == before[2:]
    assert state.fighter_b.discard_pile == [held] + before[:2]
