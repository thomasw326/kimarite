"""B11 player starts with three base stat points: 2/1/0 in style priority."""
import json
from kimarite.b10_human_session import ROSTER_PATH, roster, STYLE_PROXIES
from kimarite.b11_pending_session import PendingB11Session
from kimarite.b11_live_opening import build_resolved_b11_opening
from kimarite.models import Stat
from kimarite.styles_v5 import STYLES

def test_live_player_base_is_two_one_zero_and_ai_stays_six():
    records=json.loads(ROSTER_PATH.read_text())["decks"]
    for human in roster():
        opponent=next(x for x in roster() if x!=human)
        pending=PendingB11Session.start(human,opponent,records[human]["cards"][:3],seed=23)
        pending.confirm([])
        result=build_resolved_b11_opening(pending,seed=23)
        w=result.state.fighter_a.wrestler
        a=result.state.fighter_b.wrestler
        style=STYLES[STYLE_PROXIES.get(human,human)]
        order=list(dict.fromkeys([style.primary,style.secondary]))
        order.extend(s.value for s in (Stat.POWER,Stat.TECHNIQUE,Stat.SPIRIT) if s.value not in order)
        actual={"Power":w.base_power,"Technique":w.base_technique,"Spirit":w.base_spirit}
        assert sum(actual.values())==3
        assert actual[order[0]]==2
        assert actual[order[1]]==1
        assert sum((a.base_power,a.base_technique,a.base_spirit))==6
