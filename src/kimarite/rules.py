from __future__ import annotations

import os

from .models import BoutState, GripState, Side
from .prevention import has_negative_effect_prevention, prevent_negative_effect


GRIP_DEFENSE_MODE = os.environ.get("KIMARITE_GRIP_DEFENSE", "push").lower()
if GRIP_DEFENSE_MODE not in {"push", "momentum", "both"}:
    raise ValueError("KIMARITE_GRIP_DEFENSE must be push, momentum or both")
GRIP_DEFENSE_CARDS = frozenset({"Gain Left Grip", "Gain Right Grip", "Uwate", "Shitate"})


def _absorb_grip_defense(state: BoutState, attacker: Side, amount: int, kind: str) -> int:
    if GRIP_DEFENSE_MODE != "both" and GRIP_DEFENSE_MODE != kind:
        return amount
    defender = state.opponent_side(attacker)
    for instance in state.fighter(defender).temporary_zone:
        if amount <= 0:
            break
        if instance.card.name not in GRIP_DEFENSE_CARDS:
            continue
        # One activation per card for each protection type in the both arm.
        # The existing Push activation flag is reused for Push; Momentum is
        # tracked separately on the instance for this simulation variant.
        flag = "opponent_gained_push_while_active" if kind == "push" else "momentum_absorbed"
        if not getattr(instance, flag, False):
            setattr(instance, flag, True)
            amount -= 1
            state.log(f"{instance.card.name} absorbs 1 {kind.title()}.")
    return amount


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


def _has_temporary(state: BoutState, side: Side, card_name: str) -> bool:
    return any(
        instance.card.name == card_name
        for instance in state.fighter(side).temporary_zone
    )


def _resolve_shared_track_gain(state: BoutState, side: Side, amount: int, kind: str) -> None:
    if amount < 0:
        raise ValueError("amount must be non-negative")
    if amount == 0 or state.winner is not None:
        return
    if kind not in {"momentum", "push"}:
        raise ValueError(f"unknown track kind: {kind}")

    amount = _absorb_grip_defense(state, side, amount, kind)
    if amount == 0:
        return

    sign = state.sign(side)
    current = state.momentum if kind == "momentum" else state.position
    target = current + sign * amount
    excess = _distance_past_cap(target)
    clamped = max(TRACK_MIN, min(TRACK_MAX, target))

    if kind == "momentum":
        state.momentum = clamped
        state.fighter(side).gained_momentum_this_turn = True
        state.log(f"{state.fighter(side).wrestler.name} gains {amount} Momentum.")
        next_kind = "push"
    else:
        state.position = clamped
        state.fighter(side).gained_push_this_turn = True
        state.log(f"{state.fighter(side).wrestler.name} gains {amount} Push.")
        next_kind = "momentum"

    if excess == 0:
        return

    # Overflow converts 1:1. If the destination track is already capped for
    # the same wrestler, conversion would loop forever; that is an immediate win.
    if _track_at_favorable_cap(state, side, next_kind):
        losing_side = state.opponent_side(side)
        if kind == "push" and _has_temporary(state, losing_side, "Use the Tawara"):
            state.log(
                f"Use the Tawara prevents {state.fighter(losing_side).wrestler.name} "
                "from losing to Push."
            )
            return

        method = "Yorikiri" if total_grip(state, side) > 0 else "Oshidashi"
        state.declare_winner(side, method)
        return

    _resolve_shared_track_gain(state, side, excess, next_kind)


def gain_momentum(state: BoutState, side: Side, amount: int) -> None:
    _resolve_shared_track_gain(state, side, amount, "momentum")


def lose_momentum(state: BoutState, side: Side, amount: int) -> None:
    gain_momentum(state, state.opponent_side(side), amount)


def _break_sidestep_from_push(state: BoutState, side: Side) -> None:
    """A Push against Side-by-Side breaks Sidestep before that Push resolves."""
    owner = state.side_by_side_owner
    if owner is None or owner is side:
        return

    distance = state.side_by_side_distance
    state.position = state.sign(side) * distance
    state.side_by_side_owner = None
    state.side_by_side_distance = 0

    fighter = state.fighter(owner)
    for instance in list(fighter.temporary_zone):
        if instance.card.name == "Sidestep":
            fighter.temporary_zone.remove(instance)
            fighter.discard_pile.append(instance.card)
            state.log(
                f"{state.fighter(side).wrestler.name}'s Push breaks Sidestep; "
                f"{state.fighter(side).wrestler.name} takes the favorable orientation."
            )
            break


def gain_push(state: BoutState, side: Side, amount: int) -> None:
    if amount <= 0 or state.winner is not None:
        return

    defending_side = state.opponent_side(side)
    if _has_temporary(state, defending_side, "Hold Position"):
        if not prevent_negative_effect(
            state,
            side,
            source="Hold Position",
            description="prevent Push gain",
        ):
            state.log(
                f"Hold Position prevents {state.fighter(side).wrestler.name} from gaining Push."
            )
            return

    # Sidestep only breaks after Push has survived prevention/suppression.
    _break_sidestep_from_push(state, side)

    for instance in state.fighter(defending_side).temporary_zone:
        instance.opponent_gained_push_while_active = True

    _resolve_shared_track_gain(state, side, amount, "push")

    if _has_temporary(state, defending_side, "Use the Tawara"):
        gain_momentum(state, defending_side, 1)


def gain_position(state: BoutState, side: Side, amount: int) -> None:
    if amount < 0:
        raise ValueError("amount must be non-negative")
    state.position = max(
        TRACK_MIN,
        min(TRACK_MAX, state.position + state.sign(side) * amount),
    )
    state.log(f"{state.fighter(side).wrestler.name} gains {amount} Position.")


def lose_position(state: BoutState, side: Side, amount: int) -> None:
    if amount < 0:
        raise ValueError("amount must be non-negative")
    state.fighter(side).lost_position_this_turn = amount > 0
    gain_position(state, state.opponent_side(side), amount)


def gain_power(state: BoutState, side: Side, amount: int) -> None:
    fighter = state.fighter(side)
    fighter.power += amount
    state.log(f"{fighter.wrestler.name} gains {amount} Power.")


def lose_power(state: BoutState, side: Side, amount: int) -> None:
    fighter = state.fighter(side)
    fighter.power -= amount
    state.log(f"{fighter.wrestler.name} loses {amount} Power.")


def grip_benefits_suppressed(state: BoutState, side: Side) -> bool:
    return _has_temporary(state, state.opponent_side(side), "Kannuki")


def effective_total_grip(
    state: BoutState,
    side: Side,
    *,
    consume_prevention: bool = False,
) -> int:
    """Return usable Grip without mutating state during inspection.

    If Kannuki suppresses Grip and Shiko Stomp is available, pure callers see
    the protected Grip as usable. Actual gameplay callers may set
    consume_prevention=True to spend Shiko Stomp on that negative effect.
    """
    if not grip_benefits_suppressed(state, side):
        return state.fighter(side).total_grip

    if not has_negative_effect_prevention(state, side):
        return 0

    if consume_prevention:
        prevent_negative_effect(
            state,
            side,
            source="Kannuki",
            description="suppress benefits from existing Grip",
        )
    return state.fighter(side).total_grip


def establish_grip(state: BoutState, side: Side, hand: str) -> None:
    fighter = state.fighter(side)
    if grip_benefits_suppressed(state, side):
        if not prevent_negative_effect(
            state,
            side,
            source="Kannuki",
            description="prevent establishing Grip",
        ):
            state.log(f"Kannuki prevents {fighter.wrestler.name} from establishing Grip.")
            return
    attr = _grip_attr(hand)
    current = getattr(fighter, attr)
    if current is GripState.NONE:
        setattr(fighter, attr, GripState.GRIP)
        state.log(f"{fighter.wrestler.name} establishes {hand.title()} Grip.")


def improve_grip(state: BoutState, side: Side, hand: str, amount: int = 1) -> None:
    fighter = state.fighter(side)
    if grip_benefits_suppressed(state, side):
        if not prevent_negative_effect(
            state,
            side,
            source="Kannuki",
            description="prevent improving Grip",
        ):
            state.log(f"Kannuki prevents {fighter.wrestler.name} from improving Grip.")
            return
    attr = _grip_attr(hand)
    current = int(getattr(fighter, attr))
    updated = GripState(min(int(GripState.DEEP), current + amount))
    setattr(fighter, attr, updated)
    state.log(f"{fighter.wrestler.name} improves {hand.title()} Grip to {updated.name}.")


def reduce_grip(state: BoutState, side: Side, amount: int = 1, hand: str | None = None) -> None:
    fighter = state.fighter(side)
    if _has_temporary(state, side, "Morozashi"):
        state.log(f"Morozashi prevents {fighter.wrestler.name}'s Grip from being reduced.")
        return
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
            state.fighter(state.opponent_side(side)).opponent_grip_reduced_this_turn = True


def total_grip(state: BoutState, side: Side) -> int:
    return state.fighter(side).total_grip


def _grip_attr(hand: str) -> str:
    normalized = hand.strip().lower()
    if normalized == "left":
        return "left_grip"
    if normalized == "right":
        return "right_grip"
    raise ValueError("hand must be 'left' or 'right'")
