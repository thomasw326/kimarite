from unittest.mock import patch

from kimarite.models import BoutState, Card, FighterState, Side, Wrestler
from kimarite.playing import play_card


def test_duplicate_kimarite_grants_play_per_additional_copy():
    first = Card(90001, "Yorikiri", is_kimarite=True)
    second = Card(90002, "Yorikiri", is_kimarite=True)
    third = Card(90003, "Yorikiri", is_kimarite=True)
    other = Card(90004, "Oshidashi", is_kimarite=True)
    wrestler = Wrestler("Canary", 1, 1, 1, first, first, first)
    fighter = FighterState(wrestler=wrestler, hand=[first, second, third, other])
    opponent = FighterState(wrestler=wrestler)
    state = BoutState(fighter_a=fighter, fighter_b=opponent)
    with patch("kimarite.playing.can_play_card", return_value=True), patch(
        "kimarite.playing.resolve_kimarite_play_effect"
    ):
        play_card(state, Side.A, first)
        assert fighter.plays_remaining == 1
        play_card(state, Side.A, second)
        assert fighter.plays_remaining == 1
        play_card(state, Side.A, third)
        assert fighter.plays_remaining == 1
        play_card(state, Side.A, other)
        assert fighter.plays_remaining == 0
    assert [c.name for c in fighter.kimarite_zone] == [
        "Yorikiri", "Yorikiri", "Yorikiri", "Oshidashi"
    ]
