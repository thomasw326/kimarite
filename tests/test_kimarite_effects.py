from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext
from kimarite.models import BoutState, Card, FighterState, GripState, Side, Wrestler
from kimarite.playing import play_card


def wrestler(name: str) -> Wrestler:
    blank = Card(7000 + len(name), f"{name} Blank")
    return Wrestler(name, 0, 0, 0, blank, blank, blank)


def test_starting_kimarite_does_not_get_play_bonus_just_for_being_in_zone():
    yorikiri = card_by_name("Yorikiri")
    a = wrestler("A")
    b = wrestler("B")
    bout = BoutState(
        FighterState(a, kimarite_zone=[yorikiri]),
        FighterState(b),
    )
    bout.fighter_a.left_grip = GripState.GRIP

    assert bout.position == 0


def test_played_yorikiri_gets_position_bonus_with_grip():
    yorikiri = card_by_name("Yorikiri")
    a = wrestler("A")
    b = wrestler("B")
    bout = BoutState(
        FighterState(a, hand=[yorikiri]),
        FighterState(b),
    )
    bout.fighter_a.left_grip = GripState.GRIP

    play_card(bout, Side.A, yorikiri)

    assert bout.position == 1
    assert yorikiri in bout.fighter_a.kimarite_zone


def test_played_oshitaoshi_gains_power_when_momentum_positive():
    oshitaoshi = card_by_name("Oshitaoshi")
    a = wrestler("A")
    b = wrestler("B")
    bout = BoutState(
        FighterState(a, hand=[oshitaoshi], power=5),
        FighterState(b),
        momentum=1,
    )

    play_card(bout, Side.A, oshitaoshi)

    assert bout.fighter_a.power == 6


def test_draw_two_keep_one_loses_if_only_one_card_remains():
    katasukashi = card_by_name("Katasukashi")
    a = wrestler("A")
    b = wrestler("B")
    bout = BoutState(
        FighterState(
            a,
            hand=[katasukashi],
            draw_pile=[Card(7999, "Last Card")],
        ),
        FighterState(b),
    )

    play_card(
        bout,
        Side.A,
        katasukashi,
        context=EffectContext(choices={"use_optional": True}),
    )

    assert bout.winner is Side.B
    assert bout.win_method == "Exhaustion"
