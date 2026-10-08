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


def test_headlong_charge_stays_only_in_temporary_zone_after_play():
    card = card_by_name("Headlong Charge")
    bout = bout_with_hand([card])

    play_card(bout, Side.A, card)

    assert [x.card.name for x in bout.fighter_a.temporary_zone] == ["Headlong Charge"]
    assert card not in bout.fighter_a.discard_pile


def test_headlong_disruption_loses_three_momentum():
    card = card_by_name("Headlong Charge")
    bout = bout_with_hand([card])
    play_card(bout, Side.A, card)
    instance = bout.fighter_a.temporary_zone[0]

    remove_temporary(bout, Side.A, instance, disrupted=True)

    assert bout.momentum == -2  # +1 on play, then -3 for disruption
    assert card in bout.fighter_a.discard_pile


def test_attempt_two_handed_grip_resolves_at_next_turn_start():
    card = card_by_name("Attempt Two-Handed Grip")
    bout = bout_with_hand([card])
    play_card(bout, Side.A, card)

    resolve_start_of_turn_temporaries(bout, Side.A)

    assert bout.fighter_a.left_grip is GripState.GRIP
    assert bout.fighter_a.right_grip is GripState.GRIP
    assert not bout.fighter_a.temporary_zone


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


def test_use_tawara_converts_opponent_push_to_momentum():
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
    assert bout.momentum == 1
