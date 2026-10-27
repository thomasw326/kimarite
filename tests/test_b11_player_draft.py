"""Player draft: current-deck-aware Kimarite minimum and ceiling."""
import pytest

from kimarite.b11_player_draft import (
    STARTERS, AVAILABLE, options_for, validate_draft, deal_block,
)
from kimarite.b11_pending_session import PendingB11Session
from kimarite.b11_live_opening import build_resolved_b11_opening


def pick_through(starting, seed=9001, choice=lambda offered: offered[0]):
    picks=[]
    while len(starting)+len(picks)<28:
        offered=options_for(list(starting),picks,seed)
        assert len(offered)==3 and len(set(offered))==3
        assert not (set(offered)&set(starting+picks))
        picks.append(choice(offered))
    return picks


def test_first_tournament_starters_and_forced_third_kimarite():
    starting=list(STARTERS)
    assert len(starting)==8
    first=options_for(starting,[],7)
    assert all(AVAILABLE[n].is_kimarite for n in first)
    picks=pick_through(starting,7)
    full=validate_draft(starting,picks,7)
    assert len(full)==len(set(full))==28
    assert 3<=sum(AVAILABLE[n].is_kimarite for n in full)<=8
    assert len(deal_block(full,123))==9


def test_no_forced_kimarite_if_starting_with_three():
    extra=next(name for name,c in AVAILABLE.items() if c.is_kimarite and name not in STARTERS)
    starting=[*STARTERS,extra]
    offers=options_for(starting,[],11)
    assert len(offers)==3
    assert any(not AVAILABLE[n].is_kimarite for n in [
        *[n for n in AVAILABLE if n not in starting and not AVAILABLE[n].is_kimarite]
    ])
    full=validate_draft(starting,pick_through(starting,11),11)
    assert len(full)==28


def test_eight_starting_kimarite_never_offers_another():
    extras=[n for n,c in AVAILABLE.items() if c.is_kimarite and n not in STARTERS][:6]
    starting=[*STARTERS,*extras]
    assert sum(AVAILABLE[n].is_kimarite for n in starting)==8
    picks=[]
    for _ in range(28-len(starting)):
        offered=options_for(starting,picks,17)
        assert all(not AVAILABLE[n].is_kimarite for n in offered)
        picks.append(offered[0])
    assert len(validate_draft(starting,picks,17))==28


def test_invalid_choice_and_repeated_card_rejected():
    starting=list(STARTERS)
    picks=pick_through(starting,20)
    picks[1]=picks[0]
    with pytest.raises(ValueError):
        validate_draft(starting,picks,20)


def test_drafted_deck_is_used_to_start_b11_bout():
    starting=list(STARTERS)
    picks=pick_through(starting,51)
    deck=validate_draft(starting,picks,51)
    pending=PendingB11Session.start(
        "Arm Controller","The Technician",deck[:3],drafted_deck=deck,
        created_stats={"power":2,"technique":1,"spirit":0},
    )
    pending.confirm([0,1,2])
    result=build_resolved_b11_opening(pending)
    human=result.state.fighter_a
    assert human.wrestler.base_power==2
    assert len(human.draw_pile)+len(human.hand)+len(human.discard_pile)+len(human.kimarite_zone)<=28


def test_inherited_copy_counts_as_physical_starter_and_cannot_be_drafted():
    starting=[*STARTERS,"Oshi"]
    first=options_for(starting,[],222)
    assert "Oshi" not in first
    assert all(AVAILABLE[n].is_kimarite for n in first)
    picks=pick_through(starting,222)
    deck=validate_draft(starting,picks,222)
    assert deck.count("Oshi")==2
    assert len(deck)==28
    pending=PendingB11Session.start(
        "Arm Controller","The Technician",["Oshi","Yorikiri","Oshidashi"],
        drafted_deck=deck,
    )
    pending.confirm([0])
    assert len(pending.prepare_resolution().draw_pile)+len(pending.prepare_resolution().retained_hand)<=28


def test_draft_is_deterministic_given_same_seed_and_current_deck():
    s=list(STARTERS)
    assert options_for(s,[],1234)==options_for(s,[],1234)
    first=options_for(s,[],1234)
    assert options_for(s,[first[0]],1234)==options_for(s,[first[0]],1234)
