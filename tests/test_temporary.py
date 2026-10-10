from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext
from kimarite.models import BoutState, Card, FighterState, GripState, Side, Wrestler
from kimarite.playing import play_card
from kimarite.rules import gain_push
from kimarite.temporary import remove_temporary, resolve_start_of_turn_temporaries


def wrestler(name: str) -> Wrestler:
    blank = Card(9900 + len(name), f"{name} Blank")
    return Wrestler(name, 0, 0, 0, blank, blank, blank)


def bout_with_hand(cards):
    return BoutState(
        FighterState(wrestler("A"), hand=list(cards)),
        FighterState(wrestler("B")),
    )


def test_headlong_charge_sacrifices_kimarite_for_momentum_and_push():
    card = card_by_name("Headlong Charge")
    kimarite = card_by_name("Yorikiri")
    bout = bout_with_hand([card])
    bout.fighter_a.kimarite_zone.append(kimarite)

    play_card(
        bout, Side.A, card,
        context=EffectContext(choices={"sacrifice_kimarite": 0}),
    )

    assert bout.momentum == 1
    assert bout.position == 1
    assert bout.fighter_a.kimarite_zone == []
    assert kimarite in bout.fighter_a.discard_pile
    assert card in bout.fighter_a.discard_pile
    assert not bout.fighter_a.temporary_zone


def test_headlong_charge_can_decline_sacrifice():
    card = card_by_name("Headlong Charge")
    kimarite = card_by_name("Yorikiri")
    bout = bout_with_hand([card])
    bout.fighter_a.kimarite_zone.append(kimarite)

    play_card(
        bout, Side.A, card,
        context=EffectContext(choices={"sacrifice_kimarite": None}),
    )

    assert bout.momentum == 0
    assert bout.position == 0
    assert bout.fighter_a.kimarite_zone == [kimarite]
    assert not bout.fighter_a.temporary_zone


def test_headlong_charge_without_kimarite_grants_no_bonus():
    card = card_by_name("Headlong Charge")
    bout = bout_with_hand([card])

    play_card(bout, Side.A, card)

    assert bout.momentum == 0
    assert bout.position == 0
    assert not bout.fighter_a.temporary_zone


def test_attempt_two_handed_grip_resolves_at_next_turn_start():
    card = card_by_name("Attempt Two-Handed Grip")
    bout = bout_with_hand([card])
    play_card(bout, Side.A, card)

    resolve_start_of_turn_temporaries(bout, Side.A)

    assert bout.fighter_a.left_grip is GripState.GRIP
    assert bout.fighter_a.right_grip is GripState.GRIP
    assert not bout.fighter_a.temporary_zone
    assert bout.temporary_outcomes[-1] == (
        Side.A,
        "Attempt Two-Handed Grip",
        "survived",
    )


def test_immovable_tracks_opponent_push_and_denies_survival_momentum():
    card = card_by_name("Immovable")
    bout = bout_with_hand([card])
    play_card(bout, Side.A, card)
    gain_push(bout, Side.B, 1)

    resolve_start_of_turn_temporaries(bout, Side.A)

    assert bout.momentum == 0


def test_hold_position_prevents_opponent_push_while_active():
    card = card_by_name("Hold Position")
    bout = bout_with_hand([card])
    play_card(bout, Side.A, card)

    gain_push(bout, Side.B, 2)

    assert bout.position == 0


def test_use_tawara_prevents_push_without_gaining_momentum():
    card = card_by_name("Use the Tawara")
    bout = bout_with_hand([card])
    play_card(
        bout,
        Side.A,
        card,
        context=EffectContext(choices={"lose_position_for_power": False}),
    )

    gain_push(bout, Side.B, 1)

    assert bout.position == -1
    assert bout.momentum == 0


def test_sidestep_survives_and_takes_favorable_orientation_on_momentum_tie():
    card = card_by_name("Sidestep")
    bout = bout_with_hand([card])
    bout.position = -2

    play_card(bout, Side.A, card)

    assert bout.position == 0
    assert bout.side_by_side_owner is Side.A
    assert bout.side_by_side_distance == 2

    resolve_start_of_turn_temporaries(bout, Side.A)

    assert bout.position == 2
    assert bout.side_by_side_owner is None
    assert not bout.fighter_a.temporary_zone


def test_opponent_push_is_zero_while_sidestep_remains():
    card = card_by_name("Sidestep")
    bout = bout_with_hand([card])
    bout.position = 2

    play_card(bout, Side.A, card)
    gain_push(bout, Side.B, 1)

    assert bout.side_by_side_owner is Side.A
    assert any(x.card.name == "Sidestep" for x in bout.fighter_a.temporary_zone)
    assert bout.position == 0  # No Push while Side-by-Side is active.


def test_prevented_push_does_not_break_sidestep():
    sidestep = card_by_name("Sidestep")
    hold = card_by_name("Hold Position")
    bout = bout_with_hand([sidestep, hold])

    play_card(bout, Side.A, sidestep)
    play_card(bout, Side.A, hold)
    gain_push(bout, Side.B, 1)

    assert bout.side_by_side_owner is Side.A
    assert any(x.card.name == "Sidestep" for x in bout.fighter_a.temporary_zone)
    assert bout.position == 0
