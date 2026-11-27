"""Player draft: current-deck-aware Kimarite minimum and ceiling."""
import pytest

from kimarite.b11_player_draft import (
    STARTERS, AVAILABLE, options_for, validate_draft, deal_block, grow_deck,
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


@pytest.mark.parametrize("starting", [
    [],
    ["Oshi"],
    ["Oshi", "Tsuki"],
])
def test_inherited_draft_allows_zero_one_or_two_starting_cards(starting):
    """A losing tournament must not require consolation filler cards."""
    seed = 9010 + len(starting)
    offer = options_for(starting, [], seed)
    assert len(offer) == 3
    assert all(AVAILABLE[name].is_kimarite for name in offer)
    picks = pick_through(starting, seed)
    deck = validate_draft(starting, picks, seed)
    assert len(picks) == 28 - len(starting)
    assert len(deck) == 28
    assert 3 <= sum(AVAILABLE[name].is_kimarite for name in deck) <= 8
    assert len(deal_block(deck, 1024)) == 9


def test_twelve_inherited_cards_require_sixteen_more_picks():
    """A perfect-tournament rollover has no forced default eight-card suite."""
    starting = sorted(
        name for name, card in AVAILABLE.items() if not card.is_kimarite
    )[:12]
    seed = 9020
    picks = pick_through(starting, seed)
    assert len(picks) == 16
    deck = validate_draft(starting, picks, seed)
    assert deck[:12] == starting
    assert len(deck) == 28
    assert sum(AVAILABLE[name].is_kimarite for name in deck) >= 3


def test_starting_card_maximum_and_copy_limits_still_apply():
    with pytest.raises(ValueError, match="0–28 cards"):
        options_for(list(STARTERS) * 4, [], 9030)
    with pytest.raises(ValueError, match="at most two copies"):
        options_for(["Oshi", "Oshi", "Oshi"], [], 9030)


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


def test_duplicate_original_once_and_deal_its_copy():
    s=list(STARTERS)
    picks=pick_through(s,87)
    deck,ids=grow_deck(s,picks,87,[0,3,10])
    assert len(deck)==31
    assert len(set(ids))==31
    assert ids[28]=="duplicate:0"
    assert deck[28]==deck[0]
    assert deck[29]==deck[3]
    for seed in range(25):
        dealt=deal_block(deck,seed,ids)
        assert len(dealt)==9
        assert len({c["instance_id"] for c in dealt})==9
        assert all(c["name"]==deck[ids.index(c["instance_id"])] for c in dealt)
    with pytest.raises(ValueError):
        grow_deck(s,picks,87,[0,0])
    with pytest.raises(ValueError):
        grow_deck(s,picks,87,[0,True])
    with pytest.raises(ValueError):
        grow_deck(s,picks,87,list(range(13)))


def test_full_twelve_growth_and_live_start_accepts_duplicate_kimarite():
    s=list(STARTERS)
    picks=pick_through(s,99)
    deck,ids=grow_deck(s,picks,99,list(range(12)))
    assert len(deck)==40
    pending=PendingB11Session.start(
        "Arm Controller","The Technician",deck[:3],drafted_deck=deck,
        created_stats={"power":2,"technique":1,"spirit":0},
    )
    pending.confirm([0,1])
    result=build_resolved_b11_opening(pending)
    assert result.state.fighter_a.wrestler.base_power==2


def test_mawashi_reversal_drafts_and_legacy_drafts_still_validate():
    from kimarite.catalog import B12_CARD_POOL, card_by_id

    name = "Mawashi Reversal"
    card = AVAILABLE[name]
    assert card_by_id(card.card_id) is card
    assert (card.power, card.technique, card.spirit) == (1, 2, 0)
    assert card not in B12_CARD_POOL
    starting = list(STARTERS)
    for seed in range(100):
        picks = pick_through(starting, seed, lambda offered: name if name in offered else offered[0])
        if name in picks:
            break
    assert name in validate_draft(starting, picks, seed)
    assert "Renzoku" not in picks

    old_picks = []
    while len(starting) + len(old_picks) < 28:
        old_picks.append(options_for(starting, old_picks, seed, legacy=True)[0])
    assert validate_draft(starting, old_picks, seed) == starting + old_picks


def test_retirement_preserves_pre_retirement_draft_and_owned_cards():
    from kimarite.b11_player_draft import OWNED_CARD_POOL
    starting = list(STARTERS)
    for seed in range(100):
        picks = []
        while len(starting) + len(picks) < 28:
            offered = options_for(starting, picks, seed, pre_retirement=True)
            picks.append("Renzoku" if "Renzoku" in offered else offered[0])
        if "Renzoku" in picks:
            break
    assert "Renzoku" in picks
    assert validate_draft(starting, picks, seed) == starting + picks
    assert "Renzoku" not in AVAILABLE and "Renzoku" in OWNED_CARD_POOL
    assert len(deal_block(starting + picks, 123)) == 9
    inherited = ["Renzoku"]
    assert "Renzoku" not in options_for(inherited, [], seed)
