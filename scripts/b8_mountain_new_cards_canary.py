"""Small gameplay assertions for trial-only Mountain cards (no test-library dependency)."""
from __future__ import annotations

import b8_mountain_ankogata_tsuriotoshi_1000 as experiment
from kimarite.models import BoutState, Card, FighterState, GripState, Side, TemporaryInstance, Wrestler
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.kimarite import kimarite_is_satisfied
from kimarite import ai, playing

def fighter(name, power, left=0, right=0):
    dummy = Card(9990, "Shove", 1)
    w = Wrestler(name, 4, 1, 1, dummy, dummy, dummy)
    return FighterState(w, draw_pile=[dummy], power=power,
                        left_grip=GripState(left), right_grip=GripState(right))

def main():
    experiment.install()
    config = experiment.snapshot()
    assert len(config)==5 and all(sum(x.values())==40 for x in config.values())
    mountain = config["Mountain"]
    assert mountain["Tsuriotoshi"]==1 and mountain["Ankogata"]==2
    assert "Tottari" not in mountain and mountain["Ottsuke"]==mountain["Kannuki"]==1
    ank = Card(9991, "Ankogata", 3)
    tsu = Card(9992, "Tsuriotoshi", 2, 1, 0, True)

    # Gain +1 Power BEFORE thresholds, and no negative effect at Power <6.
    s = BoutState(fighter("Mountain",4), fighter("Grappler",4,2,2))
    resolve_exchange_effect(s, Side.A, ank, EffectContext())
    assert s.fighter_a.power==5 and s.fighter_a.is_stable
    assert s.fighter_b.total_grip==4

    # Power 5 -> 6 causes one-level reduction in BOTH hands.
    s = BoutState(fighter("Mountain",5), fighter("Grappler",4,2,2))
    resolve_exchange_effect(s, Side.A, ank, EffectContext())
    assert s.fighter_a.power==6 and s.fighter_b.total_grip==2
    assert s.fighter_b.left_grip==s.fighter_b.right_grip==GripState.GRIP

    # Power 8 -> 9 removes all opposing normal/deep Grips instead.
    s = BoutState(fighter("Mountain",8), fighter("Grappler",4,2,2))
    resolve_exchange_effect(s, Side.A, ank, EffectContext())
    assert s.fighter_a.power==9 and s.fighter_b.total_grip==0

    # Shiko Stomp stops the single hostile reduction/removal (not the Power or Stable).
    s = BoutState(fighter("Mountain",8), fighter("Grappler",4,2,2))
    s.fighter_b.temporary_zone.append(TemporaryInstance(Card(9,"Shiko Stomp"),0,"exchange"))
    resolve_exchange_effect(s,Side.A,ank,EffectContext())
    assert s.fighter_a.power==9 and s.fighter_a.is_stable
    assert s.fighter_b.total_grip==4 and not s.fighter_b.temporary_zone

    # Existing Morozashi suppression remains effective even at Power 9+.
    s = BoutState(fighter("Mountain",8), fighter("Grappler",4,2,2))
    s.fighter_b.temporary_zone.append(TemporaryInstance(Card(10,"Morozashi"),0,"exchange"))
    resolve_exchange_effect(s,Side.A,ank,EffectContext())
    assert s.fighter_b.total_grip==4

    # Count Grip LEVELS (normal=1, deep=2); check both seats and exact 12/13 edge.
    s = BoutState(fighter("Mountain",7,2,2), fighter("Grappler",10))
    s.momentum=1
    assert not kimarite_is_satisfied(s,Side.A,tsu)  # 4 + 7 + 1 = 12
    s.momentum=2
    assert kimarite_is_satisfied(s,Side.A,tsu)      # 4 + 7 + 2 = 13
    s = BoutState(fighter("Grappler",10), fighter("Mountain",10))
    s.momentum=-3
    assert kimarite_is_satisfied(s,Side.B,tsu)      # 0 + 10 + 3 = 13
    s.momentum=-2
    assert not kimarite_is_satisfied(s,Side.B,tsu)

    # Three genuine alternative choices, not one AI-forced mode.
    s = BoutState(fighter("Mountain",7),fighter("Grappler",7))
    options=ai._contexts_for_card(s,Side.A,tsu,None)
    assert {x.choice("mode") for x in options}=={"power","momentum","grip"}
    for mode in ("power","momentum","grip"):
        s=BoutState(fighter("Mountain",7),fighter("Grappler",7))
        s.fighter_a.hand=[tsu]
        playing.play_card(s,Side.A,tsu,context=EffectContext(choices={"mode":mode}))
        assert tsu in s.fighter_a.kimarite_zone
        assert (s.fighter_a.power==8) == (mode=="power")
        assert (s.momentum==1) == (mode=="momentum")
        assert (s.fighter_a.total_grip==1) == (mode=="grip")

    print("PASS: Mountain trial 40, threshold 5/6/9, Stable, both Grip hands, protection, Tsuriotoshi total 12/13, 3 AI choices")

if __name__ == "__main__":
    main()
