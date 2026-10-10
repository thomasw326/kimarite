from kimarite.catalog import CARD_POOL, card_by_name
from kimarite.effects import EffectContext
from kimarite.models import BoutState, Card, FighterState, Side, Wrestler
from kimarite.playing import play_card
from kimarite.temporary import resolve_start_of_turn_temporaries
from kimarite.turns import apply_start_of_turn_exhaustion


def make_bout(hand=(), draw=(), discard=(), power=5):
    blank = Card(9999, "Blank")
    a = Wrestler("A", 0, 0, 0, blank, blank, blank)
    b = Wrestler("B", 0, 0, 0, blank, blank, blank)
    return BoutState(
        FighterState(
            a,
            hand=list(hand),
            draw_pile=list(draw),
            discard_pile=list(discard),
            power=power,
        ),
        FighterState(b),
    )


def test_power_water_generates_six_cantrips():
    water = card_by_name("Power Water")
    bout = make_bout(hand=[water], draw=[Card(101, "Other")])
    play_card(bout, Side.A, water)
    assert sum(c.name == "Power Water Cantrip" for c in bout.fighter_a.draw_pile) == 6
    assert len(bout.fighter_a.draw_pile) == 7


def test_cantrips_are_not_in_starting_pool():
    assert not any(c.name == "Power Water Cantrip" for c in CARD_POOL)


def test_power_water_shuffle_reproducibility():
    water = card_by_name("Power Water")
    draw = [Card(i, f"Card {i}") for i in range(100, 120)]
    first = make_bout(hand=[water], draw=draw)
    second = make_bout(hand=[water], draw=draw)
    play_card(first, Side.A, water)
    play_card(second, Side.A, water)
    assert first.fighter_a.draw_pile == second.fighter_a.draw_pile


def test_cantrip_recovers_selected_discard():
    cantrip = Card(62, "Power Water Cantrip")
    target = Card(110, "Target")
    other = Card(111, "Other")
    bout = make_bout(
        hand=[cantrip],
        draw=[Card(112, "Drawn")],
        discard=[target, other],
    )
    play_card(
        bout, Side.A, cantrip,
        context=EffectContext(choices={"discard_index": 0}),
    )
    assert target in bout.fighter_a.hand
    assert target not in bout.fighter_a.discard_pile


def test_cantrip_grants_play_and_draws():
    cantrip = Card(62, "Power Water Cantrip")
    drawn = Card(112, "Drawn")
    bout = make_bout(hand=[cantrip], draw=[drawn])
    play_card(bout, Side.A, cantrip)
    assert bout.fighter_a.plays_remaining == 2
    assert drawn in bout.fighter_a.hand


def test_salt_throw_recycles_bottom_discard():
    salt = card_by_name("Salt Throw")
    bottom = Card(120, "Bottom")
    top = Card(121, "Top")
    bout = make_bout(
        hand=[salt],
        draw=[Card(122, "Existing")],
        discard=[top, bottom],
    )
    play_card(bout, Side.A, salt)
    resolve_start_of_turn_temporaries(bout, Side.A)
    assert bout.fighter_a.draw_pile[-1] == bottom
    assert bout.fighter_a.discard_pile == [top]


def test_salt_throw_persists():
    salt = card_by_name("Salt Throw")
    bout = make_bout(hand=[salt], draw=[Card(130, "Existing")])
    play_card(bout, Side.A, salt)
    resolve_start_of_turn_temporaries(bout, Side.A)
    resolve_start_of_turn_temporaries(bout, Side.A)
    assert [t.card.name for t in bout.fighter_a.temporary_zone] == ["Salt Throw"]


def test_exhaustion_at_seven_discards():
    for count, expected_power in [(6, 5), (7, 4), (8, 4), (9, 4)]:
        discard = [Card(i, str(i)) for i in range(150, 150 + count)]
        bout = make_bout(
            draw=[Card(140, "Draw")],
            discard=discard,
            power=5,
        )
        apply_start_of_turn_exhaustion(bout, Side.A)
        assert bout.fighter_a.power == expected_power
        assert bout.winner is None

