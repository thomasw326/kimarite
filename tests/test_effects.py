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


def test_oshi_gains_push_play_and_draw():
    oshi = card_by_name("Oshi")
    bout = bout_with_hand([oshi])

    play_card(bout, Side.A, oshi)

    assert bout.position == 1
    assert bout.fighter_a.plays_remaining == 2
    assert bout.fighter_a.cards_played_this_turn == 1
    assert bout.fighter_a.hand[0].name == "Draw A"
    assert bout.fighter_a.discard_pile[-1].name == "Oshi"


def test_tsuppari_chains_after_oshi():
    oshi = card_by_name("Oshi")
    tsuppari = card_by_name("Tsuppari")
    bout = bout_with_hand([oshi, tsuppari])
    bout.fighter_a.draw_pile = [Card(8101, "Draw A"), Card(8102, "Draw B")]

    play_card(bout, Side.A, oshi)
    play_card(bout, Side.A, tsuppari)

    assert bout.momentum == 1
    assert bout.position == 2
    assert [c.name for c in bout.fighter_a.played_this_turn] == ["Oshi", "Tsuppari"]
    assert bout.fighter_a.plays_remaining == 2


def test_tsuki_requires_choice_only_when_both_opposing_grips_exist():
    tsuki = card_by_name("Tsuki")
    bout = bout_with_hand([tsuki])
    bout.fighter_b.left_grip = GripState.GRIP
    bout.fighter_b.right_grip = GripState.DEEP

    try:
        play_card(bout, Side.A, tsuki)
    except ChoiceRequired as exc:
        assert exc.choice_name == "grip"
        assert exc.options == ["left", "right"]
    else:
        raise AssertionError("Tsuki should require a Grip choice when both are present")


def test_gain_right_grip_improves_existing_grip():
    card = card_by_name("Gain Right Grip")
    bout = bout_with_hand([card])
    bout.fighter_a.right_grip = GripState.GRIP

    play_card(bout, Side.A, card)

    assert bout.fighter_a.right_grip is GripState.DEEP
    assert bout.position == 0


def test_regain_balance_recovers_negative_momentum():
    card = card_by_name("Regain Balance")
    bout = bout_with_hand([card])
    bout.momentum = -2

    play_card(bout, Side.A, card)

    assert bout.momentum == 0


def test_belt_slap_uses_recorded_spirit_advantage():
    belt = card_by_name("Belt Slap")
    a = wrestler("A", spirit=3, primary=Stat.SPIRIT, secondary=Stat.POWER)
    b = wrestler("B", spirit=0)
    bout = BoutState(FighterState(a, hand=[belt]), FighterState(b))
    comparison = compare_tachiai(a, b)

    play_card(bout, Side.A, belt, context=EffectContext(comparison=comparison))

    assert bout.position == 1
    assert bout.momentum == 1


def test_ottsuke_removes_grip_temporary_and_rewards_momentum_push():
    from kimarite.temporary import add_temporary

    ottsuke = card_by_name("Ottsuke")
    morozashi = card_by_name("Morozashi")
    bout = bout_with_hand([ottsuke])
    bout.fighter_b.left_grip = GripState.GRIP
    add_temporary(bout, Side.B, morozashi, phase="exchange")

    play_card(
        bout,
        Side.A,
        ottsuke,
        context=EffectContext(
            choices={
                "mode": "remove_card",
                "card_target": 0,
            }
        ),
    )

    assert not bout.fighter_b.temporary_zone
    assert bout.momentum == 1
    assert bout.position == 1


def test_draw_effect_with_empty_draw_pile_is_immediate_exhaustion_loss():
    tsuki = card_by_name("Tsuki")
    bout = bout_with_hand([tsuki])
    bout.fighter_a.draw_pile = []

    play_card(bout, Side.A, tsuki)

    assert bout.winner is Side.B
    assert bout.win_method == "Exhaustion"
    assert bout.fighter_a.hand == []
    assert any("attempts to draw" in entry for entry in bout.event_log)


def test_ottsuke_records_kimarite_removal():
    ottsuke = card_by_name("Ottsuke")
    tsuridashi = card_by_name("Tsuridashi", prefer_starting_kimarite=True)
    bout = bout_with_hand([ottsuke])
    bout.fighter_b.kimarite_zone = [tsuridashi]

    play_card(
        bout,
        Side.A,
        ottsuke,
        context=EffectContext(
            choices={
                "mode": "remove_card",
                "card_target": 0,
            }
        ),
    )

    assert bout.kimarite_removals == [(Side.A, "Tsuridashi")]
    assert bout.fighter_b.kimarite_zone == []


def test_shikiri_exchange_rewards_technique_advantage():
    card = card_by_name("Shikiri")
    a = wrestler("A", technique=4, primary=Stat.TECHNIQUE)
    b = wrestler("B", technique=0)
    bout = BoutState(FighterState(a, hand=[card]), FighterState(b))
    play_card(bout, Side.A, card, context=EffectContext(comparison=compare_tachiai(a, b)))
    assert bout.momentum == 1
    assert bout.position == 1


def test_shikiri_exchange_without_threshold_only_gains_momentum():
    card = card_by_name("Shikiri")
    bout = bout_with_hand([card])
    play_card(bout, Side.A, card, context=EffectContext(comparison=compare_tachiai(bout.fighter_a.wrestler, bout.fighter_b.wrestler)))
    assert bout.momentum == 1
    assert bout.position == 0
