from kimarite.catalog import card_by_name
from kimarite.effects import ChoiceRequired, EffectContext
from kimarite.models import BoutState, Card, FighterState, GripState, Side, Stat, Wrestler
from kimarite.playing import play_card
from kimarite.tachiai import compare_tachiai


def wrestler(name: str, *, power=0, technique=0, spirit=0, primary=Stat.POWER, secondary=Stat.TECHNIQUE):
    blank = Card(9000 + len(name), f"{name} Blank")
    return Wrestler(name, power, technique, spirit, blank, blank, blank, primary=primary, secondary=secondary)


def bout_with_hand(cards):
    a = wrestler("A")
    b = wrestler("B")
    return BoutState(
        FighterState(a, hand=list(cards), draw_pile=[Card(8001, "Draw A"), Card(8002, "Draw B")]),
        FighterState(b),
    )


def test_oshi_gains_push_and_play_and_draws():
    oshi = card_by_name("Oshi")
    bout = bout_with_hand([oshi, Card(8999, "Cost")])
    bout.momentum = 1

    play_card(bout, Side.A, oshi)

    assert bout.position == 1
    assert bout.fighter_a.plays_remaining == 2
    assert bout.fighter_a.cards_played_this_turn == 1
    assert [c.name for c in bout.fighter_a.hand] == ["Draw A"]
    assert [c.name for c in bout.fighter_a.discard_pile] == ["Cost", "Draw B", "Oshi"]
    assert bout.fighter_a.draw_pile == []  # Oshi mills after drawing


def test_tsuppari_chains_after_oshi():
    oshi = card_by_name("Oshi")
    tsuppari = card_by_name("Tsuppari")
    bout = bout_with_hand([oshi, tsuppari, Card(8999, "Cost")])
    bout.fighter_a.draw_pile = [Card(8101, "Draw A"), Card(8102, "Draw B"), Card(8103, "Draw C"), Card(8104, "Draw D"), Card(8105, "Draw E")]

    play_card(bout, Side.A, oshi)
    play_card(bout, Side.A, tsuppari)

    # Tsuppari's approved B11 chain supplies Push, not a Momentum penalty.
    assert bout.momentum == 0
    assert bout.position == 2
    assert [c.name for c in bout.fighter_a.played_this_turn] == ["Oshi", "Tsuppari"]
    assert bout.fighter_a.plays_remaining == 2
    assert bout.winner is None
    assert bout.fighter_a.draw_pile == []
    assert [c.name for c in bout.fighter_a.hand] == ["Draw A", "Draw C"]
    assert [c.name for c in bout.fighter_a.discard_pile] == ["Cost", "Draw B", "Oshi", "Draw D", "Draw E", "Tsuppari"]


def test_tsuppari_standalone_draws_one_and_mills_two():
    card = card_by_name("Tsuppari")
    bout = bout_with_hand([card])
    bout.fighter_a.draw_pile = [Card(8201, "Draw"), Card(8202, "Mill A"), Card(8203, "Mill B"), Card(8204, "Keep")]
    play_card(bout, Side.A, card)
    assert bout.position == 0
    assert bout.momentum == 0
    assert bout.fighter_a.plays_remaining == 2
    assert [c.name for c in bout.fighter_a.hand] == ["Draw"]
    assert [c.name for c in bout.fighter_a.discard_pile] == ["Mill A", "Mill B", "Tsuppari"]
    assert [c.name for c in bout.fighter_a.draw_pile] == ["Keep"]
    assert bout.winner is None


def test_tsuki_requires_choice_only_when_both_opposing_grips_exist():
    tsuki = card_by_name("Tsuki")
    bout = bout_with_hand([tsuki])
    bout.momentum = 1
    bout.fighter_b.left_grip = GripState.GRIP
    bout.fighter_b.right_grip = GripState.DEEP

    try:
        play_card(bout, Side.A, tsuki)
    except ChoiceRequired as exc:
        assert exc.choice_name == "grip"
        assert exc.options == ["left", "right"]
    else:
        raise AssertionError("Tsuki should require a Grip choice when both are present")


def test_gain_right_grip_deepens_existing_grip_and_grants_temporary_shield():
    card = card_by_name("Gain Right Grip")
    bout = bout_with_hand([card])
    bout.fighter_a.right_grip = GripState.GRIP

    play_card(bout, Side.A, card)

    assert bout.fighter_a.right_grip is GripState.DEEP
    assert bout.position == 0
    assert [t.card.name for t in bout.fighter_a.temporary_zone] == ["Gain Right Grip"]


def test_regain_balance_recovers_negative_momentum():
    card = card_by_name("Regain Balance")
    bout = bout_with_hand([card])
    bout.momentum = -2

    play_card(bout, Side.A, card)

    # One step of Momentum recovery under approved B10 rules.
    assert bout.momentum == -1
    assert bout.fighter_a.power == 2


def test_belt_slap_always_gains_momentum_and_push_requires_spirit_advantage():
    belt = card_by_name("Belt Slap")
    for side in (Side.A, Side.B):
        for advantage in (-3, -1, 0, 2, 3, 4):
            own = wrestler("Owner", spirit=max(advantage, 0), primary=Stat.SPIRIT, secondary=Stat.POWER)
            foe = wrestler("Opponent", spirit=max(-advantage, 0), primary=Stat.SPIRIT, secondary=Stat.POWER)
            a, b = (own, foe) if side is Side.A else (foe, own)
            bout = BoutState(FighterState(a), FighterState(b), active_side=side)
            bout.fighter(side).hand = [belt]
            comparison = compare_tachiai(a, b)
            play_card(bout, side, belt, context=EffectContext(comparison=comparison))
            assert bout.position * bout.sign(side) == (1 if advantage >= 3 else 0)
            assert bout.momentum * bout.sign(side) == 1
            assert bout.winner is None


def test_ottsuke_reduces_grip_and_prevents_new_grip():
    from kimarite.rules import improve_grip
    from kimarite.temporary import add_temporary, resolve_start_of_turn_temporaries
    ottsuke = card_by_name("Ottsuke")
    bout = bout_with_hand([ottsuke])
    bout.fighter_b.left_grip = GripState.DEEP
    add_temporary(bout, Side.B, card_by_name("Hold Position"), phase="exchange")
    play_card(bout, Side.A, ottsuke)
    assert bout.fighter_b.left_grip is GripState.GRIP
    assert len(bout.fighter_b.temporary_zone) == 1
    assert bout.momentum == 1
    improve_grip(bout, Side.B, "right")
    assert bout.fighter_b.right_grip is GripState.NONE
    resolve_start_of_turn_temporaries(bout, Side.A)
    improve_grip(bout, Side.B, "right")
    assert bout.fighter_b.right_grip is GripState.GRIP


def test_draw_effect_with_empty_draw_pile_is_immediate_exhaustion_loss():
    tsuki = card_by_name("Tsuki")
    bout = bout_with_hand([tsuki])
    bout.fighter_a.draw_pile = []

    play_card(bout, Side.A, tsuki)

    assert bout.winner is Side.B
    assert bout.win_method == "Exhaustion"
    assert bout.fighter_a.hand == []
    assert any("attempts to draw" in entry for entry in bout.event_log)


def test_ottsuke_preserves_opposing_kimarite():
    ottsuke = card_by_name("Ottsuke")
    tsuridashi = card_by_name("Tsuridashi", prefer_starting_kimarite=True)
    bout = bout_with_hand([ottsuke])
    bout.fighter_b.kimarite_zone = [tsuridashi]
    play_card(bout, Side.A, ottsuke)
    assert bout.kimarite_removals == []
    assert bout.fighter_b.kimarite_zone == [tsuridashi]
    assert bout.momentum == 1
