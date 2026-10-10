"""R20 combat adapter tests. Local only; no tournament jobs."""
from kimarite.effects import EffectContext
from kimarite.models import BoutState, Card, FighterState, GripState, Side, Wrestler
from kimarite.r20_gauntlet import ScheduledBout, load_arms
from kimarite.r20_gauntlet_bouts import prepare_fixture
from kimarite.r20_variant_rules import build_variant_card, variant_predicate, variant_exchange
from kimarite.temporary import add_temporary, remove_temporary
from kimarite.turns import start_exchange_turn
from kimarite.tachiai import compare_tachiai


def sample(identifier="OKD-1"):
    arm = build_variant_card(identifier, card_id=65001)
    basic = Card(610, "Oshi", 0, 0, 1)
    cards = [Card(701 + i, f"Filler{i}", 1, 1, 1) for i in range(14)]
    a = Wrestler("Generic A", 2, 2, 1, arm, basic, cards[0])
    b = Wrestler("Generic B", 2, 2, 1, Card(780, "Yorikiri", 1, 1, 1, True), basic, cards[1])
    fa = FighterState(a, draw_pile=list(cards), hand=cards[:2], kimarite_zone=[arm], power=5)
    fb = FighterState(b, draw_pile=list(cards), hand=cards[2:4], kimarite_zone=[b.starting_kimarite], power=6)
    return BoutState(fa, fb, r20_active=True), arm


def test_all_70_arms_have_executable_rule_and_exchange():
    arms = load_arms()
    assert len(arms) == 70
    for index, arm in enumerate(arms):
        state, _ = sample()
        assert isinstance(variant_predicate(state, Side.A, arm.arm_id), bool)
        card = build_variant_card(arm.arm_id, card_id=70000+index)
        variant_exchange(state, Side.A, card, EffectContext())


def test_reversal_family_requires_own_turn_completion():
    state, _ = sample()
    state.position, state.momentum = 1, 1
    state.fighter_a.successful_reversal_this_turn = True
    assert variant_predicate(state, Side.A, "OKD-2")
    assert not variant_predicate(state, Side.A, "OKD-1")
    assert variant_predicate(state, Side.A, "OKT-3")


def test_reversal_cannot_be_credited_on_disruption():
    state, _ = sample()
    inst = add_temporary(state, Side.A, Card(627, "Immovable", 3, 0, 0), phase="exchange")
    remove_temporary(state, Side.A, inst, disrupted=True)
    assert not state.fighter_a.successful_reversal_this_turn


def test_henka_survives_and_finishes_before_start_of_turn_check():
    state, variant = sample()
    state.position, state.momentum = 2, 1
    state.fighter_a.first_exchange_turn = False
    add_temporary(state, Side.A, Card(629, "Henka", 0, 4, 0), phase="exchange")
    start_exchange_turn(state, Side.A, compare_tachiai(state.fighter_a.wrestler, state.fighter_b.wrestler))
    assert state.fighter_a.successful_reversal_this_turn
    assert state.winner is Side.A
    assert state.winning_kimarite_card_id == variant.card_id


def test_seat_mirroring_keeps_each_identity_deck_fixed():
    arm = next(a for a in load_arms() if a.arm_id == "UWD-2")
    def make(seat):
        bout = ScheduledBout(arm.arm_id, arm.kimarite, "shuffled", "12-02", 12, 37, seat, 90123)
        return prepare_fixture(arm, bout)
    a, card_a, side_a = make("A")
    b, card_b, side_b = make("B")
    assert card_a == card_b
    assert a.fighter(side_a).draw_pile == b.fighter(side_b).draw_pile
    assert a.opponent(side_a).draw_pile == b.opponent(side_b).draw_pile
