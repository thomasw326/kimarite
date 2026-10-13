"""Salt Throw is permanent until removed; removal exhausts it."""
from types import SimpleNamespace

from kimarite.models import Side
from kimarite.temporary import add_temporary, remove_temporary, resolve_start_of_turn_temporaries


def _state():
    salt = SimpleNamespace(name="Salt Throw", card_id=1)
    recycled = SimpleNamespace(name="Oshi", card_id=2)
    fighter = SimpleNamespace(
        wrestler=SimpleNamespace(name="Test"),
        temporary_zone=[], discard_pile=[recycled], draw_pile=[],
    )
    state = SimpleNamespace(
        turn_number=1, side_by_side_owner=None, temporary_outcomes=[],
        reversal_completions=[], log=lambda text: None,
        fighter=lambda side: fighter,
    )
    return state, fighter, salt, recycled


def test_salt_throw_recycles_every_turn_without_leaving_temporary():
    state, fighter, salt, recycled = _state()
    instance = add_temporary(state, Side.A, salt, phase="exchange")
    resolve_start_of_turn_temporaries(state, Side.A)
    assert fighter.temporary_zone == [instance]
    assert fighter.draw_pile == [recycled]
    assert fighter.discard_pile == []
    fighter.discard_pile.append(fighter.draw_pile.pop())
    resolve_start_of_turn_temporaries(state, Side.A)
    assert fighter.temporary_zone == [instance]
    assert fighter.draw_pile == [recycled]


def test_salt_throw_is_exhausted_if_disrupted_or_removed():
    for disrupted in (True, False):
        state, fighter, salt, _ = _state()
        instance = add_temporary(state, Side.A, salt, phase="exchange")
        remove_temporary(state, Side.A, instance, disrupted=disrupted)
        assert not fighter.temporary_zone
        assert salt not in fighter.discard_pile
        assert salt not in fighter.draw_pile


def test_shiko_stomp_exhausts_when_disrupted_instead_of_being_recycled():
    state, fighter, _, recycled = _state()
    shiko = SimpleNamespace(name="Shiko Stomp", card_id=3)
    instance = add_temporary(state, Side.A, shiko, phase="exchange")
    resolve_start_of_turn_temporaries(state, Side.A)
    assert fighter.temporary_zone == [instance]
    remove_temporary(state, Side.A, instance, disrupted=True)
    assert shiko not in fighter.discard_pile
    assert shiko not in fighter.draw_pile
    assert recycled in fighter.discard_pile
