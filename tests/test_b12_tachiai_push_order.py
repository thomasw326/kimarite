"""Tachiai: pool Spirit and card Push before original stepped Power blocks."""
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


def test_only_spirit_push_is_blocked_at_original_power_threshold():
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
    # Spirit diff 3 => 1, Explosive Step +1 => 2, Power lead 2 => 1 block.
    resolve_prepared_tachiai(state, comp)
    assert state.position == 1


def test_full_power_block_prevents_card_bonus_ringout():
    state, comp = setup(a_power=0, a_spirit=1,
                        a_prepared="Explosive Step — Fumikomi",
                        b_power=7, position=2)
    # Spirit 1 + card 1 = 2, fully blocked by Power lead 7 (3 blocks).
    resolve_prepared_tachiai(state, comp)
    assert state.position == 2
    assert state.winner is None


def test_power_initialization_and_buffs_are_not_double_counted():
    state, comp = setup(a_power=0, a_spirit=4, b_power=3)
    # Crossing Power lead +3 to +4 increases blocks from one to two.
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
    # Spirit 2 (A), Shove 1 (B) => net 1 (A); opening Power is tied.
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

def test_oshi_reveal_orbs_increase_effective_power_before_blocking():
    state, comp = setup(a_power=0, a_spirit=3,
                        a_prepared="Oshi", b_power=2, b_spirit=0)
    # Oshi reveals Tsuki (1 Power) and Shove (2 Power), then stops.
    # Power must update in both comparison and fighter state before
    # the defender's lead is calculated: A 1+3 Power, B 3 Power.
    state.fighter_a.draw_pile[:] = [
        card_by_name("Tsuki"), card_by_name("Shove"), BLANK
    ]
    resolve_prepared_tachiai(state, comp)
    assert comp.wrestler_a.power == 4
    assert state.fighter_a.power == 4
    assert state.fighter_b.power == 3
    # Spirit diff 4 => two Push and the defender has no Power lead.
    assert state.position == 2


@pytest.mark.parametrize("power_lead,blocked", [
    (-1, 0), (0, 0), (1, 1), (2, 1), (3, 1),
    (4, 2), (5, 2), (6, 2), (7, 3), (9, 3),
    (10, 4), (12, 4), (13, 5),
])
def test_power_block_thresholds_apply_after_all_card_push(power_lead, blocked):
    # No Spirit lead, so all six Push come from the prepared-card pool.
    state, comp = setup(a_power=0, a_spirit=0,
                        b_power=power_lead, b_spirit=0)
    side, pushed = apply_tachiai_power_push(
        state, comp, extra_push={Side.A: 6, Side.B: 0},
    )
    assert side is Side.A
    assert pushed == 6 - blocked
    # Position can ring out at >3; check the resolved Push count above.


def test_spirit_and_card_push_share_same_stepped_power_block():
    # Spirit advantage 7 => 3 Push, bonus +2 => 5 Push total.
    # Defender Power +4 => precisely TWO Push blocked (not four).
    state, comp = setup(a_power=0, a_spirit=7, b_power=4)
    side, pushed = apply_tachiai_power_push(
        state, comp, extra_push={Side.A: 2, Side.B: 0},
    )
    assert side is Side.A
    assert pushed == 3
    assert state.position == 3


def test_power_difference_beyond_threshold_cannot_reverse_push():
    state, comp = setup(a_power=0, a_spirit=4, b_power=13)
    side, pushed = apply_tachiai_power_push(state, comp)
    assert side is Side.A
    assert pushed == 0
    assert state.position == 0


def test_power_bonus_of_one_does_not_add_a_block_off_threshold():
    state, comp = setup(a_power=0, a_spirit=7, b_power=1)
    state.fighter_b.power += 1  # Power +1 -> +2: remains one block.
    assert apply_tachiai_power_push(state, comp) == (Side.A, 2)
    assert state.position == 2
