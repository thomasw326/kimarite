"""Isolated R21 experimental mechanics. Never modify live Kimarite definitions.

Unchanged references delegate to the tested R20 implementation. Proposed R21
variants override only the explicitly documented rule, orb, or Exchange axis.
"""
from __future__ import annotations

from functools import lru_cache

from .effects import EffectContext, add_play, draw_from_look, draw_one
from .kimarite import power_advantage, relative_momentum, relative_position
from .models import BoutState, Card, Side
from .r20_variant_rules import (
    variant_exchange as _r20_exchange,
    variant_predicate as _r20_predicate,
    variant_progress as _r20_progress,
)
from .r21_gauntlet import load_arms
from .r21_search import search_for_reversal
from .rules import effective_total_grip
from .models import GripState

PREFIX = "R21:"

@lru_cache(maxsize=1)
def _arms():
    return {a.arm_id: a for a in load_arms()}

@lru_cache(maxsize=1)
def _references():
    import json
    from .r21_gauntlet import MANIFEST_PATH
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {a["id"]: a["r20_reference"] for a in data["arms"]}

def arm_id(card: Card) -> str | None:
    if not card.name.startswith(PREFIX):
        return None
    key = card.name[len(PREFIX):]
    if key not in _arms():
        raise KeyError(f"Unknown experimental R21 arm {key}")
    return key

def build_variant_card(identifier: str, *, card_id: int) -> Card:
    arm = _arms()[identifier]
    return Card(card_id, PREFIX + identifier,
                arm.orbs.count("🟣"), arm.orbs.count("🟢"),
                arm.orbs.count("🟠"), True)

def variant_predicate(state: BoutState, side: Side, identifier: str) -> bool:
    reference = _references()[identifier]
    f, o = state.fighter(side), state.opponent(side)
    mom = relative_momentum(state, side)
    pos = relative_position(state, side)
    adv = power_advantage(state, side)
    hand_adv = len(f.hand) - len(o.hand)
    grip = effective_total_grip(state, side)
    other_grip = effective_total_grip(state, state.opponent_side(side))
    reversal = bool(f.successful_reversal_this_turn)

    # All these checks retain their unaffected requirements from the R20 spec.
    if identifier == "R21-HIK-C2-MN3":
        return grip >= 1 and mom <= -3 and pos >= 0
    if identifier == "R21-KAT-H5-T2":
        return other_grip == 0 and mom >= 1 and hand_adv >= 5
    if identifier == "R21-KIR-P3-HA3":
        return reversal and adv <= -3 and hand_adv >= 3
    if identifier == "R21-UTC-F2-MN2":
        return f.gained_momentum_this_turn and pos == -3 and mom <= -2
    if identifier == "R21-R25-UWD-M2-EX":
        return f.left_grip.value >= 1 and grip > 0 and mom >= 2 and adv <= -5
    if identifier == "R21-UWA-C1-M2":
        return f.left_grip is GripState.DEEP and grip > 0 and mom >= 2 and pos >= 0
    if identifier == "R21-TSR-P6":
        return grip >= 3 and pos >= 0 and f.power >= 6
    if identifier == "R21-SUK-P3":
        return f.total_grip == 0 and mom >= 2 and hand_adv >= 3
    if identifier == "R21-KIR-H3":
        return reversal and adv <= -1 and hand_adv >= 1 and len(f.hand) >= 3
    if identifier == "R21-KIR-H4":
        return reversal and adv <= -1 and hand_adv >= 1 and len(f.hand) >= 4
    if identifier == "R21-KIR-P2":
        return reversal and adv <= -2 and hand_adv >= 1
    if identifier == "R21-KIR-P3":
        return reversal and adv <= -3 and hand_adv >= 1
    if identifier == "R21-UWD-P4":
        return f.left_grip.value >= 1 and grip > 0 and mom >= 1 and adv <= -4
    if identifier == "R21-KAT-M2":
        return other_grip == 0 and mom >= 2 and hand_adv >= 4
    if identifier == "R21-KAT-H5":
        return other_grip == 0 and mom >= 1 and hand_adv >= 5
    return _r20_predicate(state, side, reference)

def variant_exchange(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    identifier = arm_id(card)
    if identifier is None:
        raise ValueError("Not an experimental R21 kimarite")
    if state.disable_kimarite_exchange_effects:
        return
    if identifier == "R21-R24-UWD-NE":
        return
    if identifier in {"R21-OKD-RS", "R21-OKT-RS"}:
        search_for_reversal(state.fighter(side))
        return
    if identifier == "R21-KAT-H5-T2":
        if relative_momentum(state, side) >= 1:
            fighter = state.fighter(side)
            if fighter.discard_pile:
                selected = context.choice("discard_index")
                if not isinstance(selected, int) or not 0 <= selected < len(fighter.discard_pile):
                    selected = len(fighter.discard_pile) - 1
                fighter.hand.append(fighter.discard_pile.pop(selected))
        return
    if identifier == "R21-UTC-F2-MN2":
        if relative_position(state, side) < 0:
            draw_from_look(state, side, look=2, keep=1, required_draws=1)
        return
    if identifier == "R21-HIK-RS":
        search_for_reversal(state.fighter(side))
        return
    if identifier == "R21-UTC-F2":
        if relative_position(state, side) < 0:
            draw_from_look(state, side, look=2, keep=1, required_draws=1)
        return
    if identifier == "R21-UTC-P1":
        if relative_position(state, side) < 0:
            add_play(state, side, 1)
            if state.winner is None:
                draw_one(state, side)
        return
    if identifier == "R21-TSO-D1":
        add_play(state, side, 1)
        if state.winner is None:
            draw_one(state, side)
        return
    # YTA-H1 combines the tested YTA-1 Exchange with YTA-3's win.
    reference = "YTA-1" if identifier == "R21-YTA-H1" else _references()[identifier]
    original = Card(card.card_id, "R20:" + reference,
                    card.power, card.technique, card.spirit, True)
    _r20_exchange(state, side, original, context)

def variant_progress(state: BoutState, side: Side, identifier: str) -> float:
    if variant_predicate(state, side, identifier):
        return 1.0
    # R20's advisory AI heuristic applies to the same named finish family;
    # cap below 1 for modified thresholds. Only predicate is authoritative.
    return min(0.99, _r20_progress(state, side, _references()[identifier]))
