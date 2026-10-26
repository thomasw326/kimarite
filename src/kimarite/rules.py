from __future__ import annotations

from .models import BoutState, GripState, Side
from .prevention import has_negative_effect_prevention, prevent_negative_effect


TRACK_MIN = -3
TRACK_MAX = 3
POSITION_MIN = -4
POSITION_MAX = 4


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

    sign = state.sign(side)
    current = state.momentum if kind == "momentum" else state.position
    target = current + sign * amount
    if kind == "push" and sign * target >= 5:
        state.position = sign * POSITION_MAX
        state.fighter(side).gained_push_this_turn = True
        state.log(f"{state.fighter(side).wrestler.name} crosses the ring boundary.")
        state.win_source = "ringout"
        state.declare_winner(side, "Yorikiri" if total_grip(state, side) > 0 else "Oshidashi")
        return
    if kind == "push":
        excess = 0
        clamped = max(POSITION_MIN, min(POSITION_MAX, target))
    else:
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

    if excess == 0 or kind == "momentum":
        return

    # Overflow converts 1:1. If the destination track is already capped for
    # the same wrestler, conversion would loop forever; that is an immediate win.
    if _track_at_favorable_cap(state, side, next_kind):
        method = "Yorikiri" if total_grip(state, side) > 0 else "Oshidashi"
        state.win_source = "ringout"
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

    # Side-by-Side suppresses ALL Push, whether entered through Sidestep
    # or Spin Away, including Push from the initiating wrestler.
    if state.side_by_side_owner is not None:
        state.log("Side-by-Side reduces all Push to 0.")
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

    # The four basic Grip cards each protect against one point of incoming Push.
    # The protection is a real Temporary, discarded when consumed or at its
    # owner's next turn, and multiple shields can each absorb one Push.
    defender = state.fighter(defending_side)
    for instance in list(defender.temporary_zone):
        if amount <= 0:
            break
        if instance.card.name in {"Gain Left Grip", "Gain Right Grip", "Uwate", "Shitate"}:
            defender.temporary_zone.remove(instance)
            defender.discard_pile.append(instance.card)
            state.temporary_outcomes.append((defending_side, instance.card.name, "protected"))
            state.log(f"{instance.card.name} prevents 1 incoming Push.")
            amount -= 1
    if amount <= 0:
        return

    # B9 Henka: protect exactly one incoming Push while active.
    for temporary in defender.temporary_zone:
        if amount <= 0:
            break
        if temporary.card.name == "Henka" and not getattr(temporary, "henka_prevention_used", False):
            temporary.henka_prevention_used = True
            amount -= 1
            state.log("Henka prevents the first 1 incoming Push.")
    if amount <= 0:
        return

    # Sidestep only breaks after Push has survived prevention/suppression.
    _break_sidestep_from_push(state, side)

    for instance in state.fighter(defending_side).temporary_zone:
        instance.opponent_gained_push_while_active = True

    _resolve_shared_track_gain(state, side, amount, "push")


def gain_position(state: BoutState, side: Side, amount: int) -> None:
    if amount < 0:
        raise ValueError("amount must be non-negative")
    if state.winner is not None:
        return
    target = state.position + state.sign(side) * amount
    if state.sign(side) * target >= 5:
        state.position = state.sign(side) * POSITION_MAX
        state.win_source = "ringout"
        state.declare_winner(side, "Yorikiri" if total_grip(state, side) > 0 else "Oshidashi")
        return
    state.position = max(POSITION_MIN, min(POSITION_MAX, target))
    state.log(f"{state.fighter(side).wrestler.name} gains {amount} Position.")


def lose_position(state: BoutState, side: Side, amount: int, *, source: str = "unspecified") -> None:
    if amount < 0:
        raise ValueError("amount must be non-negative")
    if amount > 0:
        state.fighter(side).lost_position_this_turn = True
        state.position_loss_events.append((side, state.turn_number, source, amount))
    gain_position(state, state.opponent_side(side), amount)


def make_unstable(state: BoutState, side: Side) -> None:
    """Apply the B9 Unstable condition until this fighter finishes its next turn."""
    fighter = state.fighter(side)
    fighter.unstable = True
    # Recovery follows the target's NEXT completed turn. If inflicted during
    # their own turn, do not recover at that turn's imminent end.
    recovery = fighter.turns_started + 1
    fighter.unstable_recovery_turn = max(fighter.unstable_recovery_turn, recovery)
    state.log(f"{state.fighter(side).wrestler.name} becomes Unstable.")


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


def gain_flexible_grip(state: BoutState, side: Side) -> None:
    """Improve whichever Grip is shallower, left on ties, up to Deep."""
    fighter = state.fighter(side)
    hand = "left" if fighter.left_grip <= fighter.right_grip else "right"
    improve_grip(state, side, hand)


def establish_grip(state: BoutState, side: Side, hand: str) -> None:
    fighter = state.fighter(side)
    if grip_benefits_suppressed(state, side):
        if not prevent_negative_effect(
            state,
            side,
            source="Kannuki",
            description="prevent establishing Grip",
        ):
            state.fighter(state.opponent_side(side)).opponent_grip_reduced_this_turn = True
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
            state.fighter(state.opponent_side(side)).opponent_grip_reduced_this_turn = True
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
            next_grip = GripState(current - 1)
            setattr(fighter, attr, next_grip)
            hand_name = "Left" if attr == "left_grip" else "Right"
            state.log(
                f"{fighter.wrestler.name}'s {hand_name} Grip decreases "
                f"({GripState(current).name} → {next_grip.name})."
            )
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
