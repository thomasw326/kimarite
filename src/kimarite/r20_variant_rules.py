"""R20 variant predicates and Exchange effects, isolated by R20:<arm_id>.

All experimental cards use distinct IDs and names. Never fall back to the
live same-name effects: an unknown experimental arm raises immediately.
"""
from __future__ import annotations

from functools import lru_cache

from .effects import EffectContext, add_play, draw_from_look, draw_one
from .kimarite import power_advantage, relative_momentum, relative_position
from .models import BoutState, Card, GripState, Side
from .prevention import prevent_negative_effect
from .rules import (
    effective_total_grip, establish_grip, gain_flexible_grip, gain_momentum,
    gain_position, gain_power, gain_push, lose_momentum, lose_position,
    reduce_grip,
)
from .r20_gauntlet import load_arms

PREFIX = "R20:"


@lru_cache(maxsize=1)
def _arms():
    return {arm.arm_id: arm for arm in load_arms()}


def arm_id(card: Card) -> str | None:
    if not card.name.startswith(PREFIX):
        return None
    ident = card.name[len(PREFIX):]
    if ident not in _arms():
        raise KeyError(f"Unregistered experimental Kimarite {card.name!r}")
    return ident


def build_variant_card(identifier: str, *, card_id: int) -> Card:
    arm = _arms()[identifier]
    return Card(card_id, PREFIX + identifier,
                arm.orbs.count("🟣"), arm.orbs.count("🟢"), arm.orbs.count("🟠"),
                True)


def variant_predicate(state: BoutState, side: Side, identifier: str) -> bool:
    if identifier not in _arms():
        raise KeyError(f"Unknown R20 variant {identifier!r}")
    group, num = identifier.split("-", 1)
    version = int(num)
    f, o = state.fighter(side), state.opponent(side)
    mom, pos, adv = relative_momentum(state, side), relative_position(state, side), power_advantage(state, side)
    grip = effective_total_grip(state, side)
    other_grip = effective_total_grip(state, state.opponent_side(side))
    cards = f.cards_played_this_turn
    hand_advantage = len(f.hand) - len(o.hand)
    reversal = getattr(f, "successful_reversal_this_turn", False)

    if group == "YOR":
        return grip >= (2 if version == 0 else 1) and mom >= (2 if version == 2 else 1) and pos >= 2
    if group == "OSH":
        return pos >= 2 and mom >= (1 if version == 1 else 2) and (
            version != 1 or adv >= 1 or state.tachiai_spirit_advantage_a * state.sign(side) >= 3)
    if group == "TSU":
        return pos >= 2 and cards >= (3 if version in (1, 2) else 4) and (version != 2 or mom >= 1)
    if group == "OTA":
        return mom >= (2 if version == 2 else 1) and f.power >= (9 if version == 3 else 8) and (
            version != 1 or pos >= 1)
    if group == "YTA":
        return grip >= (1 if version == 3 else 2) and pos >= 2 and adv >= (1 if version == 2 else 2)
    if group == "HAT":
        return mom <= -2 and (version == 3 or pos >= 0) and (
            version == 1 or f.power >= (6 if version == 3 else 5))
    if group == "HIK":
        return grip >= 1 and mom <= -2 and pos >= 0
    if group == "TOT":
        return f.total_grip == 0 and f.opponent_grip_reduced_this_turn
    if group == "UTC":
        return f.gained_momentum_this_turn and (
            (version == 1 and (pos == -3 or mom == -2)) or
            (version == 2 and mom == -2) or (version == 3 and pos == -3))
    if group == "TKT":
        return cards >= (4 if version == 3 else 3) and (
            version == 3 or (mom >= 2 and (version != 2 or pos >= 1)))
    if group == "TSR":
        return grip >= 3 and pos >= 0 and f.power >= {1: 5, 2: 7, 3: 9}[version]
    if group == "KOT":
        return other_grip == 0 and mom >= 1 and (
            (version == 1 and len(f.hand) >= 5) or
            (version == 2 and f.power >= 6) or (version == 3 and adv >= 1))
    if group == "ABI":
        return grip >= 2 and f.power >= (9 if version == 1 else 10)
    if group in {"UWA", "SHI"}:
        hand = f.left_grip if group == "UWA" else f.right_grip
        return hand is GripState.DEEP and grip > 0 and mom >= 1 and pos >= 0
    if group == "SUK":
        return f.total_grip == 0 and mom >= 2 and hand_advantage >= {1: 2, 2: 4, 3: 5}[version]
    if group == "TSO":
        return f.total_grip == 0 and mom >= (2 if version == 2 else 1) and adv <= (-3 if version == 3 else -1)
    if group == "OKD":
        return bool(reversal) and pos >= (1 if version == 2 else 2) and mom >= (0 if version == 3 else 1)
    if group == "OKT":
        return bool(reversal) and pos >= (0 if version == 2 else 1) and mom >= (1 if version == 3 else 2)
    if group == "KIR":
        return bool(reversal) and adv <= -1 and hand_advantage >= 1
    if group == "UWD":
        return grip > 0 and f.left_grip is not GripState.NONE and mom >= 1 and adv <= -{1: 1, 2: 3, 3: 5}[version]
    if group == "KAT":
        if version == 0:
            return f.total_grip == 0 and mom >= 1 and f.lost_position_this_turn
        return other_grip == 0 and mom >= 1 and (
            (version == 1 and len(f.hand) >= 5) or
            (version == 2 and hand_advantage >= 3) or
            (version == 3 and hand_advantage >= 4))
    raise KeyError(f"No R20 predicate for {identifier!r}")


def _hand_discard(state: BoutState, side: Side, context: EffectContext) -> None:
    f = state.fighter(side)
    if f.hand:
        raw = context.choice("hand_index")
        i = raw if isinstance(raw, int) and 0 <= raw < len(f.hand) else len(f.hand) - 1
        f.discard_pile.append(f.hand.pop(i))


def _opponent_discard(state: BoutState, side: Side, context: EffectContext) -> bool:
    f = state.opponent(side)
    if not f.hand:
        return False
    raw = context.choice("opponent_hand_index")
    i = raw if isinstance(raw, int) and 0 <= raw < len(f.hand) else 0
    f.discard_pile.append(f.hand.pop(i))
    return True


def _filtered_draw(state: BoutState, side: Side, count: int) -> None:
    # Looking at up to N cards is not a requirement to have N cards left.
    draw_from_look(state, side, look=count, keep=1, required_draws=1)


def variant_exchange(state: BoutState, side: Side, card: Card, context: EffectContext) -> None:
    ident = arm_id(card)
    if ident is None:
        raise ValueError("Not an experimental Kimarite")
    if state.disable_kimarite_exchange_effects:
        return
    group, num = ident.split("-", 1)
    version = int(num)
    f, o = state.fighter(side), state.opponent(side)
    mom, pos, adv = relative_momentum(state, side), relative_position(state, side), power_advantage(state, side)
    grip = effective_total_grip(state, side)

    if group == "YOR":
        if version == 3:
            if grip >= 2:
                gain_push(state, side, 1)
        elif pos >= 0:
            gain_flexible_grip(state, side)
    elif group == "OSH":
        if pos >= 1:
            gain_momentum(state, side, 1)
    elif group == "TSU":
        if version == 3 or pos >= 1:
            add_play(state, side, 1)
            if state.winner is None:
                draw_one(state, side)
    elif group == "OTA":
        if mom >= 1:
            gain_power(state, side, 1)
        if power_advantage(state, side) >= 1:
            gain_momentum(state, side, 1)
    elif group == "YTA":
        if version in (1, 2) and adv >= 1:
            gain_flexible_grip(state, side)
        if version in (1, 3) and effective_total_grip(state, side) >= 1:
            gain_power(state, side, 1)
    elif group == "HAT":
        if context.choice("use_optional") is not False and mom > -3:
            lose_momentum(state, side, 1)
            if not _opponent_discard(state, side, context):
                for _ in range(2 if version == 2 else 1):
                    if state.winner is None:
                        draw_one(state, side)
    elif group == "HIK":
        if version == 3:
            draw_one(state, side)
        else:
            _filtered_draw(state, side, 2 if version == 1 else 3)
    elif group == "TOT":
        if version == 1:
            looked = o.draw_pile[:3]
            if looked:
                raw = context.choice("opponent_deck_index")
                i = raw if isinstance(raw, int) and 0 <= raw < len(looked) else 0
                o.discard_pile.append(o.draw_pile.pop(i))
        elif not _opponent_discard(state, side, context) and version == 3:
            draw_one(state, side)
    elif group == "UTC":
        if pos < 0:
            draw_one(state, side)
    elif group == "TKT":
        add_play(state, side, 1)
        draw_one(state, side)
        if state.winner is None:
            _hand_discard(state, side, context)
    elif group == "TSR":
        gain_power(state, side, 1)
        if relative_momentum(state, side) >= 2:
            gain_power(state, side, 1)
    elif group == "KOT":
        hands = [h for h in ("left", "right") if getattr(o, h + "_grip") is not GripState.NONE]
        if hands:
            raw = context.choice("grip")
            hand = raw if raw in hands else hands[0]
            if not prevent_negative_effect(state, state.opponent_side(side), source="Kotenage",
                                           description=f"reduce {hand} Grip"):
                reduce_grip(state, state.opponent_side(side), hand=hand)
        elif context.choice("cycle_if_no_grip") is not False:
            draw_one(state, side)
            if state.winner is None:
                _hand_discard(state, side, context)
    elif group == "ABI":
        if version == 3:
            if f.power >= 7:
                gain_flexible_grip(state, side)
            if effective_total_grip(state, side) >= 1:
                gain_power(state, side, 1)
        elif f.power >= 6:
            if grip == 0:
                gain_flexible_grip(state, side)
            else:
                gain_power(state, side, 1)
    elif group in ("UWA", "SHI"):
        hand = "left" if group == "UWA" else "right"
        hand_state = getattr(f, hand + "_grip")
        if version == 3:
            if hand_state is not GripState.NONE:
                gain_momentum(state, side, 1)
        elif mom >= (0 if version == 1 else 1):
            establish_grip(state, side, hand)
    elif group == "SUK":
        if f.total_grip == 0:
            draw_one(state, side)
    elif group == "TSO":
        add_play(state, side, 1)
    elif group in ("OKD", "OKT"):
        chosen = context.choice("conversion")
        if chosen not in ("position_to_momentum", "momentum_to_position"):
            chosen = ("momentum_to_position" if pos <= mom else "position_to_momentum")
        # Neither payment may be waived. If the selected track is already at
        # the negative cap, take the other legal payment instead.
        if chosen == "position_to_momentum" and pos <= -3:
            chosen = "momentum_to_position"
        if chosen == "momentum_to_position" and mom <= -3:
            chosen = "position_to_momentum"
        if (chosen == "position_to_momentum" and pos <= -3) or (chosen == "momentum_to_position" and mom <= -3):
            from .effects import IllegalPlay
            raise IllegalPlay("R20 rear finish requires losing 1 Position or 1 Momentum.")
        if chosen == "position_to_momentum":
            lose_position(state, side, 1, source=group)
            if state.winner is None:
                gain_momentum(state, side, 2)
        else:
            lose_momentum(state, side, 1)
            if state.winner is None:
                gain_position(state, side, 2)
    elif group == "KIR":
        if version == 1:
            draw_one(state, side)
        else:
            _filtered_draw(state, side, version)
    elif group == "UWD":
        draw_one(state, side)
        if state.winner is None and f.hand:
            # May discard even if Left Grip already exists. Default AI only
            # pays the optional cost when it would establish a missing Grip.
            use = context.choice("discard_for_grip")
            if use is True or (use is None and f.left_grip is GripState.NONE):
                _hand_discard(state, side, context)
                establish_grip(state, side, "left")
    elif group == "KAT":
        if version == 0:
            if context.choice("use_optional") is True:
                lose_momentum(state, side, 1)
                if state.winner is None:
                    _filtered_draw(state, side, 2)
        elif mom >= 1:
            draw_one(state, side)
    else:
        raise KeyError(f"No Exchange effect for {ident!r}")
