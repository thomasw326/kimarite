"""Tachiai: Spirit and card Push pool BEFORE one-for-one Power blocks."""
import pytest

from kimarite.catalog import card_by_name
from kimarite.models import BoutState, Card, FighterState, Side, Wrestler
from kimarite.tachiai import apply_tachiai_power_push, compare_tachiai
from kimarite.tachiai_effects import resolve_prepared_tachiai
from kimarite.turns import apply_initial_power


BLANK = Card(99001, "Blank")


def setup(a_power, a_spirit, a_prepared="Blank",
          b_power=0, b_spirit=0, b_prepared="Blank", position=0):
    def card(name):
        return BLANK if name == "Blank" else card_by_name(name)

    a = Wrestler("A", a_power, 0, a_spirit, BLANK, card(a_prepared), BLANK)
    b = Wrestler("B", b_power, 0, b_spirit, BLANK, card(b_prepared), BLANK)
    state = BoutState(FighterState(a), FighterState(b), position=position)
    comparison = compare_tachiai(a, b)
    apply_initial_power(state, comparison)
    return state, comparison


def test_only_spirit_push_is_blocked_one_for_one_by_power_difference():
    state, comp = setup(a_power=0, a_spirit=4, b_power=1)
    # Spirit diff 4 => two Push; defender Power advantage 1 => one Push.
    assert apply_tachiai_power_push(state, comp) == (Side.A, 1)
    assert state.position == 1


def test_card_only_push_is_blocked_by_power():
    state, comp = setup(a_power=3, a_spirit=0,
                        b_power=0, b_spirit=0, b_prepared="Shove")
    assert comp.spirit_winner is None
    # Shove printed Power 2 but A has total Power 4 vs B's 3.
    resolve_prepared_tachiai(state, comp)
    assert state.position == 0
    assert state.winner is None


def test_explosive_step_bonus_and_spirit_are_blocked_in_same_pool():
    state, comp = setup(a_power=0, a_spirit=1,
                        a_prepared="Explosive Step — Fumikomi", b_power=2)
    # Spirit diff 4 => 2, Explosive Step +1 => 3, Power lead 2 => 1.
    resolve_prepared_tachiai(state, comp)
    assert state.position == 1


def test_full_power_block_prevents_card_bonus_ringout():
    state, comp = setup(a_power=0, a_spirit=1,
                        a_prepared="Explosive Step — Fumikomi",
                        b_power=3, position=2)
    # Spirit 2 + card 1 = 3, fully blocked by Power lead 3.
    resolve_prepared_tachiai(state, comp)
    assert state.position == 2
    assert state.winner is None


def test_power_initialization_and_buffs_are_not_double_counted():
    state, comp = setup(a_power=0, a_spirit=4, b_power=1)
    # +1 Power buff to the defender increases blocks by exactly one.
    state.fighter_b.power += 1
    assert apply_tachiai_power_push(state, comp) == (Side.A, 0)
    assert state.position == 0


def test_hold_position_tachiai_power_buff_blocks_card_push():
    state, comp = setup(a_power=0, a_spirit=0,
                        a_prepared="Hold Position",
                        b_power=1, b_spirit=0, b_prepared="Shove")
    assert comp.spirit_winner is None
    resolve_prepared_tachiai(state, comp)
    assert state.position == 0
    assert state.fighter_a.power == 6  # 1 base + 3 orbs + 2 Tachiai
    assert state.fighter_b.power == 4  # 1 base + 1 base + 2 orbs


def test_get_underneath_push_blocked_but_nonpush_effects_remain():
    state, comp = setup(a_power=0, a_spirit=0,
                        a_prepared="Get Underneath", b_power=2)
    resolve_prepared_tachiai(state, comp)
    assert state.position == 0
    assert state.momentum == 1


def test_opposing_card_push_is_netted_before_power_blocks():
    state, comp = setup(a_power=2, a_spirit=4,
                        b_power=0, b_spirit=0, b_prepared="Shove")
    # Spirit 2 (A), Shove 1 (B) => net 1 (A); with A Power lead, no block.
    resolve_prepared_tachiai(state, comp)
    assert state.position == 1


def test_power_lead_does_not_generate_push_by_itself():
    state, comp = setup(a_power=5, a_spirit=0, b_power=0, b_spirit=0)
    assert apply_tachiai_power_push(state, comp) == (None, 0)
    assert state.position == 0


def test_push_beyond_edge_occurs_only_after_power_blocking():
    state, comp = setup(a_power=0, a_spirit=10,
                        b_power=1, position=2)
    # Spirit advantage 10 => 4 Push, Power lead 1 => 3, still a ringout.
    resolve_prepared_tachiai(state, comp)
    assert state.winner is Side.A
    assert state.win_source == "ringout"


@pytest.mark.parametrize("extra,expected", [(1, 0), (2, 1), (3, 2)])
def test_card_only_push_pool_blocks_once_against_power(extra, expected):
    state, comp = setup(a_power=0, a_spirit=0, b_power=1, b_spirit=0)
    winner, push = apply_tachiai_power_push(
        state, comp, extra_push={Side.A: extra, Side.B: 0},
    )
    assert winner is Side.A
    assert push == expected
    assert state.position == expected
