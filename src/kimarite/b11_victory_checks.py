"""Readable B11 victory checks, matched directly to Classic Kimarite predicates.

The conditions below are display-only; the engine's predicates alone decide wins.
"""
from .kimarite import effective_total_grip, relative_momentum, relative_position, power_advantage
from .models import GripState


def victory_checks(state, side, name):
    fighter = state.fighter(side)
    foe = state.opponent(side)
    grip = effective_total_grip(state, side)
    enemy_grip = effective_total_grip(state, state.opponent_side(side))
    momentum = relative_momentum(state, side)
    position = relative_position(state, side)
    advantage = power_advantage(state, side)
    hand_diff = len(fighter.hand) - len(foe.hand)
    values = {
        "grip": grip, "enemy_grip": enemy_grip, "raw_grip": fighter.total_grip,
        "momentum": momentum, "position": position, "power": fighter.power,
        "power_advantage": advantage, "hand_diff": hand_diff,
        "hand": len(fighter.hand), "enemy_discard": len(foe.discard_pile),
        "plays": fighter.cards_played_this_turn,
        "left": fighter.left_grip.name, "right": fighter.right_grip.name,
        "stable": not fighter.unstable, "foe_unstable": foe.unstable,
        "grip_reduced": fighter.opponent_grip_reduced_this_turn,
        "gained_momentum": fighter.gained_momentum_this_turn,
        "sum": fighter.power + momentum + grip,
    }
    # (label, measured key, comparison, threshold).
    definitions = {
        "Yorikiri": [("Effective Grip","grip",">=",1),("Momentum advantage","momentum",">=",1),("Position advantage","position",">=",2)],
        "Oshidashi": [("Position advantage","position",">=",2),("Momentum advantage","momentum",">=",2)],
        "Tsukidashi": [("Position advantage","position",">=",3),("Cards played this turn","plays",">=",3)],
        "Oshitaoshi": [("Momentum advantage","momentum",">=",2),("Power","power",">=",8)],
        "Yoritaoshi": [("Effective Grip","grip",">=",1),("Position advantage","position",">=",2),("Power advantage","power_advantage",">=",2)],
        "Katasukashi": [("Opponent effective Grip","enemy_grip","=",0),("Opponent raw Grip","enemy_raw_grip","=",0),("Momentum advantage","momentum",">=",2),("Hand advantage","hand_diff",">=",4)],
        "Tsukiotoshi": [("Own Grip","raw_grip","=",0),("Momentum advantage","momentum",">=",1),("Power advantage","power_advantage","<=",-3),("Opponent unstable","foe_unstable","=",True)],
        "Tottari": [("Own Grip","raw_grip","=",0),("Opponent Grip reduced this turn","grip_reduced","=",True),("Opponent discard count","enemy_discard",">=",7)],
        "Uwatenage": [("Deep Left Grip","left","=","DEEP"),("Effective Grip","grip",">=",1),("Momentum advantage","momentum",">=",1),("Position advantage","position",">=",0)],
        "Shitatenage": [("Effective Grip","grip",">=",1),("Deep Right Grip","right","=","DEEP"),("Momentum advantage","momentum",">=",1),("Position advantage","position",">=",0)],
        "Hatakikomi": [("Momentum advantage","momentum","<=",-2),("Power","power",">=",6)],
        "Hikiotoshi": [("Momentum advantage","momentum","<=",-2),("Position advantage","position",">=",0),("Effective Grip","grip",">=",1)],
        "Tsukitaoshi": [("Cards played this turn","plays",">=",4)],
        "Tsuridashi": [("Effective Grip","grip",">=",3),("Position advantage","position",">=",0),("Power","power",">=",6)],
        "Kotenage": [("Opponent effective Grip","enemy_grip","=",0),("Momentum advantage","momentum",">=",1),("Cards in hand","hand",">=",5)],
        "Abisetaoshi": [("Effective Grip","grip",">=",2),("Power","power",">=",10)],
        "Kirikaeshi": [("Power advantage","power_advantage","<=",-3),("Own stable","stable","=",True),("Opponent unstable","foe_unstable","=",True),("Momentum advantage","momentum",">=",2)],
        "Okuridashi": [("Position advantage","position",">=",2),("Momentum advantage","momentum",">=",1)],
        "Okuritaoshi": [("Power","power",">=",8),("Momentum advantage","momentum",">=",1)],
        "Tsuriotoshi": [("Power + Momentum + Grip","sum",">=",15)],
        "Sukuinage": [("Own Grip","raw_grip","=",0),("Momentum advantage","momentum",">=",2),("Hand advantage","hand_diff",">=",4)],
        "Utchari": [("Gained Momentum this turn","gained_momentum","=",True),("Position advantage","position","=",-3)],
        "Uwatedashinage": [("Left Grip present","left","!=","NONE"),("Effective Grip","grip",">=",1),("Momentum advantage","momentum",">=",1),("Power advantage","power_advantage","<=",-5)],
    }
    values["enemy_raw_grip"] = foe.total_grip
    if name not in definitions:
        return []
    operators = {">=":lambda a,b:a>=b, "<=":lambda a,b:a<=b, "=":lambda a,b:a==b, "!=":lambda a,b:a!=b}
    return [{"label":label,"actual":values[key],"required":op+" "+str(threshold),"met":operators[op](values[key],threshold)}
            for label,key,op,threshold in definitions[name]]
