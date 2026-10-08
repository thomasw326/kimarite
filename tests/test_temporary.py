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
    assert bout.temporary_outcomes[-1] == (
        Side.A,
        "Headlong Charge",
        "disrupted",
    )


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


def test_opponent_push_breaks_sidestep_before_push_resolves():
    card = card_by_name("Sidestep")
    bout = bout_with_hand([card])
    bout.position = 2

    play_card(bout, Side.A, card)
    gain_push(bout, Side.B, 1)

    assert bout.side_by_side_owner is None
    assert not bout.fighter_a.temporary_zone
    assert card in bout.fighter_a.discard_pile
    # Retained distance 2 becomes favorable to B, then B's Push moves to -3.
    assert bout.position == -3


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


def test_grip_defense_absorbs_one_push_per_card_and_expires():
    from kimarite.rules import gain_push
    left = card_by_name("Gain Left Grip")
    right = card_by_name("Gain Right Grip")
    bout = bout_with_hand([left, right])
    play_card(bout, Side.A, left)
    play_card(bout, Side.A, right)
    assert len(bout.fighter_a.temporary_zone) == 2

    gain_push(bout, Side.B, 3)
    assert bout.position == -1
    gain_push(bout, Side.B, 1)
    assert bout.position == -2
    resolve_start_of_turn_temporaries(bout, Side.A)
    assert not bout.fighter_a.temporary_zone


def test_uwate_and_shitate_absorb_push_while_retaining_grip_effect():
    from kimarite.rules import gain_push
    from kimarite.models import GripState
    uwate = card_by_name("Uwate")
    shitate = card_by_name("Shitate")
    bout = bout_with_hand([uwate, shitate])
    play_card(bout, Side.A, uwate)
    play_card(bout, Side.A, shitate)
    assert bout.fighter_a.left_grip == GripState.GRIP
    assert bout.fighter_a.right_grip == GripState.GRIP
    gain_push(bout, Side.B, 2)
    assert bout.position == 0
    gain_push(bout, Side.B, 1)
    assert bout.position == -1


def test_two_handed_attempt_improves_existing_grips_on_survival():
    from kimarite.models import GripState
    attempt = card_by_name("Attempt Two-Handed Grip")
    bout = bout_with_hand([attempt])
    bout.fighter_a.left_grip = GripState.GRIP
    play_card(bout, Side.A, attempt)
    resolve_start_of_turn_temporaries(bout, Side.A)
    assert bout.fighter_a.left_grip == GripState.DEEP
    assert bout.fighter_a.right_grip == GripState.GRIP


def test_disrupted_grip_attempts_no_longer_lose_momentum():
    from kimarite.temporary import remove_temporary
    for name in ("Attempt Two-Handed Grip", "Attempt Deep Outside Grip",
                 "Attempt Deep Inside Grip"):
        card = card_by_name(name)
        bout = bout_with_hand([card])
        play_card(bout, Side.A, card)
        remove_temporary(bout, Side.A, bout.fighter_a.temporary_zone[0], disrupted=True)
        assert bout.momentum == 0
