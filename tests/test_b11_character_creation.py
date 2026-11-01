"""B11 character stats are selected rather than inferred from roster style."""
import pytest
from kimarite.b11_pending_session import PendingB11Session
from kimarite.b11_live_opening import build_resolved_b11_opening
from kimarite.b10_human_session import management_deal, roster


def make_pending(stats):
    names=[c["name"] for c in management_deal("Arm Controller", 20261021)["cards"][:3]]
    return PendingB11Session.start("Arm Controller","The Technician",names,created_stats=stats)


@pytest.mark.parametrize("stats",[
    {"power":2,"technique":1,"spirit":0},
    {"power":0,"technique":2,"spirit":1},
    {"power":1,"technique":0,"spirit":2},
])
def test_player_chosen_stats_apply_to_live_opening(stats):
    pending=make_pending(stats)
    pending.confirm([0,1,2])
    result=build_resolved_b11_opening(pending)
    human=result.state.fighter_a.wrestler
    ai=result.state.fighter_b.wrestler
    assert (human.base_power,human.base_technique,human.base_spirit)==tuple(stats[k] for k in ("power","technique","spirit"))
    assert sum([ai.base_power,ai.base_technique,ai.base_spirit])==6


@pytest.mark.parametrize("stats",[
    {"power":3,"technique":0,"spirit":0},
    {"power":1,"technique":1,"spirit":1},
    {"power":2,"technique":1},
    {"power":True,"technique":1,"spirit":0},
])
def test_invalid_stat_spreads_rejected(stats):
    with pytest.raises(ValueError):
        make_pending(stats)
