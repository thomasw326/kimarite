from kimarite.models import Side
from kimarite.setup import BoutConfig, FighterConfig, create_prepared_bout


def test_fujinokawa_tochinoshin_setup_matches_known_difficulty_zero_case():
    bout = create_prepared_bout(
        BoutConfig(
            FighterConfig(
                "Fujinokawa",
                102,
                frozenset({7, 14, 15, 16, 29, 35, 43}),
            ),
            FighterConfig(
                "Tochinoshin",
                911132,
                frozenset({18, 19, 21, 28, 31, 32, 33}),
            ),
        )
    )

    state = bout.state

    assert state.fighter_a.power == 4
    assert state.fighter_b.power == 5
    assert state.position == -1
    assert state.active_side is Side.A

    assert state.fighter_a.kimarite_zone[0].name == "Tsukitaoshi"
    assert state.fighter_b.kimarite_zone[0].name == "Tsuridashi"

    assert state.fighter_a.draw_pile[0].name == "Oshi"
    assert state.fighter_b.draw_pile[0].name == "Morozashi"
    assert state.fighter_a.draw_pile[-1].name == "Stare Down"
    assert state.fighter_b.draw_pile[-1].name == "Gain Right Grip"
