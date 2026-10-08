from __future__ import annotations

from .models import BoutState, GripState, Side


TRACK_MIN = -3
TRACK_MAX = 3


def _cap_for(side: Side) -> int:
    return TRACK_MAX if side is Side.A else TRACK_MIN


def _distance_past_cap(value: int) -> int:
    if value > TRACK_MAX:
        return value - TRACK_MAX
    if value < TRACK_MIN:
        return TRACK_MIN - value
    return 0


def _track_at_favorable_cap(state: BoutState, side: Side, kind: str) -> bool:
    cap = _cap_for(side)
    return (state.momentum if kind == "momentum" else state.position) == cap


def _resolve_shared_track_gain(state: BoutState, side: Side, amount: int, kind: str) -> None:
    if amount < 0:
        raise ValueError("amount must be non-negative")
    if amount == 0 or state.winner is not None:
        return
    if kind not in {"momentum", "push"}:
        raise ValueError(f"unknown track kind: {kind}")

    sign = state.sign(side)
    current = state.momentum if kind == "momentum" else state.position
    target = current + sign * amount
    excess = _distance_past_cap(target)
    clamped = max(TRACK_MIN, min(TRACK_MAX, target))

    if kind == "momentum":
        state.momentum = clamped
        state.log(f"{state.fighter(side).wrestler.name} gains {amount} Momentum.")
        next_kind = "push"
    else:
        state.position = clamped
        state.log(f"{state.fighter(side).wrestler.name} gains {amount} Push.")
        next_kind = "momentum"

    if excess == 0:
        return

    # Overflow converts 1:1. If the destination track is already capped for
    # the same wrestler, conversion would loop forever; that is an immediate win.
    if _track_at_favorable_cap(state, side, next_kind):
        method = "Yorikiri" if total_grip(state, side) > 0 else "Oshidashi"
        state.declare_winner(side, method)
        return

    _resolve_shared_track_gain(state, side, excess, next_kind)


def gain_momentum(state: BoutState, side: Side, amount: int) -> None:
    _resolve_shared_track_gain(state, side, amount, "momentum")


def lose_momentum(state: BoutState, side: Side, amount: int) -> None:
    gain_momentum(state, state.opponent_side(side), amount)


def gain_push(state: BoutState, side: Side, amount: int) -> None:
    _resolve_shared_track_gain(state, side, amount, "push")


def gain_position(state: BoutState, side: Side, amount: int) -> None:
    if amount < 0:
        raise ValueError("amount must be non-negative")
    state.position = max(
        TRACK_MIN,
        min(TRACK_MAX, state.position + state.sign(side) * amount),
    )
    state.log(f"{state.fighter(side).wrestler.name} gains {amount} Position.")


def lose_position(state: BoutState, side: Side, amount: int) -> None:
    gain_position(state, state.opponent_side(side), amount)


def gain_power(state: BoutState, side: Side, amount: int) -> None:
    fighter = state.fighter(side)
    fighter.power += amount
    state.log(f"{fighter.wrestler.name} gains {amount} Power.")


def lose_power(state: BoutState, side: Side, amount: int) -> None:
    fighter = state.fighter(side)
    fighter.power -= amount
    state.log(f"{fighter.wrestler.name} loses {amount} Power.")


def establish_grip(state: BoutState, side: Side, hand: str) -> None:
    fighter = state.fighter(side)
    attr = _grip_attr(hand)
    current = getattr(fighter, attr)
    if current is GripState.NONE:
        setattr(fighter, attr, GripState.GRIP)
        state.log(f"{fighter.wrestler.name} establishes {hand.title()} Grip.")


def improve_grip(state: BoutState, side: Side, hand: str, amount: int = 1) -> None:
    fighter = state.fighter(side)
    attr = _grip_attr(hand)
    current = int(getattr(fighter, attr))
    updated = GripState(min(int(GripState.DEEP), current + amount))
    setattr(fighter, attr, updated)
    state.log(f"{fighter.wrestler.name} improves {hand.title()} Grip to {updated.name}.")


def reduce_grip(state: BoutState, side: Side, amount: int = 1, hand: str | None = None) -> None:
    fighter = state.fighter(side)
    for _ in range(amount):
        if hand is not None:
            attr = _grip_attr(hand)
        else:
            # Deterministic generic reduction: reduce the deeper grip first,
            # then Left before Right on ties. Card-specific choice can override later.
            attr = (
                "left_grip"
                if int(fighter.left_grip) >= int(fighter.right_grip)
                else "right_grip"
            )
        current = int(getattr(fighter, attr))
        if current > 0:
            setattr(fighter, attr, GripState(current - 1))


def total_grip(state: BoutState, side: Side) -> int:
    return state.fighter(side).total_grip


def _grip_attr(hand: str) -> str:
    normalized = hand.strip().lower()
    if normalized == "left":
        return "left_grip"
    if normalized == "right":
        return "right_grip"
    raise ValueError("hand must be 'left' or 'right'")
