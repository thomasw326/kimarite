from kimarite.models import Side
from kimarite.setup import BoutConfig, FighterConfig, create_prepared_bout


def test_fujinokawa_tochinoshin_setup_matches_v44_tachiai_case():
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
    assert state.position == 3
    assert state.active_side is Side.A

    assert state.fighter_a.kimarite_zone[0].name == "Tsukitaoshi"
    assert state.fighter_b.kimarite_zone[0].name == "Tsuridashi"

    assert state.fighter_a.draw_pile[0].name == "Oshi"
    assert state.fighter_b.draw_pile[0].name == "Morozashi"
    assert state.fighter_a.draw_pile[-1].name == "Stare Down"
    assert state.fighter_b.draw_pile[-1].name == "Gain Right Grip"


def test_headlong_charge_prepared_card_enters_temporary_not_bottom():
    bout = create_prepared_bout(
        BoutConfig(
            FighterConfig("Houdan", 11, ranking=1),
            FighterConfig("Kotozakura", 12, ranking=2),
        )
    )
    state = bout.state

    assert any(
        instance.card.name == "Headlong Charge"
        for instance in state.fighter_a.temporary_zone
    )
    assert state.fighter_a.draw_pile[-1].name != "Headlong Charge"


def test_shiko_stomp_prepared_card_starts_in_temporary_and_persists():
    bout = create_prepared_bout(
        BoutConfig(
            FighterConfig("Hoshoryu", 13, ranking=1),
            FighterConfig("Asakoryu", 14, ranking=2),
        )
    )
    state = bout.state

    assert any(
        instance.card.name == "Shiko Stomp"
        for instance in state.fighter_a.temporary_zone
    )
    assert state.fighter_a.draw_pile[-1].name != "Shiko Stomp"


def test_exchange_only_temporary_tachiai_card_goes_to_bottom():
    bout = create_prepared_bout(
        BoutConfig(
            FighterConfig("Tamawashi", 15, ranking=1),
            FighterConfig("Ura", 16, ranking=2),
        )
    )
    state = bout.state

    assert all(
        instance.card.name != "Hold Position"
        for instance in state.fighter_a.temporary_zone
    )
    assert state.fighter_a.draw_pile[-1].name == "Hold Position"
