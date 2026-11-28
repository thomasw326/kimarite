from __future__ import annotations

from .models import BoutState, GripState, Side
from .prevention import has_negative_effect_prevention, prevent_negative_effect


TRACK_MIN = -3
TRACK_MAX = 3
POSITION_MIN = -4
POSITION_MAX = 4


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
    if kind == "momentum":
        # Approved B12 rule: cap Momentum; excess is lost, never Push.
        state.momentum = max(TRACK_MIN, min(TRACK_MAX, target))
        state.fighter(side).gained_momentum_this_turn = True
        state.log(f"{state.fighter(side).wrestler.name} gains {amount} Momentum.")
    else:
        state.position = max(POSITION_MIN, min(POSITION_MAX, target))
        state.fighter(side).gained_push_this_turn = True
        state.log(f"{state.fighter(side).wrestler.name} gains {amount} Push.")


def discard_normally(state: BoutState, side: Side, card) -> None:
    """Route ordinary hand/play discards through Meguri without changing mills.

    Mill, temporary removal, and explicit Exhaust effects use their own zones.
    """
    fighter = state.fighter(side)
    if _has_temporary(state, side, "Meguri"):
        fighter.draw_pile.append(card)
        state.log(f"Meguri returns {card.name} to the bottom of the Draw Pile.")
    else:
        fighter.discard_pile.append(card)


def trigger_ritual_draw(state: BoutState, side: Side, ritual: str) -> None:
    """Draw once per active ritual instance per turn, without recursion."""
    if state.winner is not None:
        return
    fighter = state.fighter(side)
    instances = [instance for instance in fighter.temporary_zone
                 if instance.card.name == ritual
                 and instance.last_trigger_turn != state.turn_number]
    for instance in instances:
        if state.winner is not None:
            break
        instance.last_trigger_turn = state.turn_number
        from .effects import draw_one
        state.log(f"{ritual} activates.")
        draw_one(state, side)


def gain_momentum(state: BoutState, side: Side, amount: int) -> None:
    _resolve_shared_track_gain(state, side, amount, "momentum")


def lose_momentum(state: BoutState, side: Side, amount: int) -> None:
    gain_momentum(state, state.opponent_side(side), amount)


def recover_momentum(state: BoutState, side: Side, amount: int = 1) -> None:
    """Restore negative relative Momentum toward zero, never beyond zero."""
    if amount < 0:
        raise ValueError("amount must be non-negative")
    shortfall = max(0, -state.momentum * state.sign(side))
    if shortfall:
        gain_momentum(state, side, min(shortfall, amount))


def recover_push(state: BoutState, side: Side, amount: int = 1) -> None:
    """Gain Push only while Position is negative, and only up to neutral."""
    if amount < 0:
        raise ValueError("amount must be non-negative")
    shortfall = max(0, -state.position * state.sign(side))
    if shortfall:
        gain_push(state, side, min(shortfall, amount))


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
            (fighter.exhaust_pile if instance.exhaust_on_leave else fighter.discard_pile).append(instance.card)
            state.log(
                f"{state.fighter(side).wrestler.name}'s Push breaks Sidestep; "
                f"{state.fighter(side).wrestler.name} takes the favorable orientation."
            )
            trigger_ritual_draw(state, side, "Shikiri")
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
        if instance.card.name in {"Gain Left Grip", "Gain Right Grip"}:
            defender.temporary_zone.remove(instance)
            (defender.exhaust_pile if instance.exhaust_on_leave else defender.discard_pile).append(instance.card)
            state.temporary_outcomes.append((defending_side, instance.card.name, "protected"))
            state.log(f"{instance.card.name} prevents 1 incoming Push.")
            amount -= 1
    if amount <= 0:
        return

    # Sidestep only breaks after Push has survived prevention/suppression.
    _break_sidestep_from_push(state, side)

    for instance in state.fighter(defending_side).temporary_zone:
        instance.opponent_gained_push_while_active = True

    previous_position = state.position
    _resolve_shared_track_gain(state, side, amount, "push")

    # Meguri is exhausted only when real opposing Push moves Position against
    # its owner; prevented/suppressed Push does not break the ritual.
    if state.position * state.sign(defending_side) < previous_position * state.sign(defending_side):
        from .temporary import remove_temporary
        defender = state.fighter(defending_side)
        for instance in list(defender.temporary_zone):
            if instance.card.name == "Meguri":
                instance.exhaust_on_leave = True
                remove_temporary(state, defending_side, instance, disrupted=True)


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


def make_unstable(state: BoutState, side: Side, *, source_side: Side | None = None) -> None:
    """Apply the B9 Unstable condition until this fighter finishes its next turn."""
    fighter = state.fighter(side)
    if source_side is state.opponent_side(side) and _has_temporary(state, side, "Ankogata"):
        state.log(f"Ankogata prevents {fighter.wrestler.name} from becoming Unstable.")
        return
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


def lose_power(state: BoutState, side: Side, amount: int, *, source_side: Side | None = None) -> None:
    fighter = state.fighter(side)
    if amount > 0 and source_side is state.opponent_side(side) and _has_temporary(state, side, "Ankogata"):
        state.log(f"Ankogata prevents {fighter.wrestler.name} from losing Power.")
        return
    fighter.power -= amount
    state.log(f"{fighter.wrestler.name} loses {amount} Power.")


def grip_benefits_suppressed(state: BoutState, side: Side) -> bool:
    return _has_temporary(state, state.opponent_side(side), "Kannuki")


def grip_gain_prevented(state: BoutState, side: Side) -> bool:
    return _has_temporary(state, state.opponent_side(side), "Ottsuke")


def effective_total_grip(
    state: BoutState,
    side: Side,
    *,
    consume_prevention: bool = False,
) -> int:
    """Return usable Grip without mutating state during inspection.

    If Kannuki suppresses Grip and Sonkyo is available, pure callers see
    the protected Grip as usable. Actual gameplay callers may set
    consume_prevention=True to spend Sonkyo on that negative effect.
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


def automatic_grip_hand(state: BoutState, side: Side, *, reduce: bool = False) -> str:
    """Choose shallower own/deeper opposing Grip; acting seat breaks ties."""
    fighter = state.opponent(side) if reduce else state.fighter(side)
    if fighter.left_grip == fighter.right_grip:
        return "left" if side is Side.A else "right"
    if reduce:
        return "left" if fighter.left_grip > fighter.right_grip else "right"
    return "left" if fighter.left_grip < fighter.right_grip else "right"


def gain_flexible_grip(state: BoutState, side: Side) -> None:
    """Improve whichever Grip is shallower, acting seat on ties, up to Deep."""
    improve_grip(state, side, automatic_grip_hand(state, side))


def establish_grip(state: BoutState, side: Side, hand: str) -> None:
    fighter = state.fighter(side)
    if grip_gain_prevented(state, side):
        if not prevent_negative_effect(
            state,
            side,
            source="Ottsuke",
            description="prevent establishing Grip",
        ):
            state.log(f"Ottsuke prevents {fighter.wrestler.name} from establishing Grip.")
            return
    attr = _grip_attr(hand)
    current = getattr(fighter, attr)
    if current is GripState.NONE:
        setattr(fighter, attr, GripState.GRIP)
        state.log(f"{fighter.wrestler.name} establishes {hand.title()} Grip.")


def improve_grip(state: BoutState, side: Side, hand: str, amount: int = 1) -> None:
    fighter = state.fighter(side)
    if grip_gain_prevented(state, side):
        if not prevent_negative_effect(
            state,
            side,
            source="Ottsuke",
            description="prevent improving Grip",
        ):
            state.log(f"Ottsuke prevents {fighter.wrestler.name} from improving Grip.")
            return
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
            # then attacker's seat A chooses Left, seat B Right on ties.
            attr = _grip_attr(automatic_grip_hand(state, state.opponent_side(side), reduce=True))
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
            trigger_ritual_draw(state, state.opponent_side(side), "Shikiri")


def total_grip(state: BoutState, side: Side) -> int:
    return state.fighter(side).total_grip


def _grip_attr(hand: str) -> str:
    normalized = hand.strip().lower()
    if normalized == "left":
        return "left_grip"
    if normalized == "right":
        return "right_grip"
    raise ValueError("hand must be 'left' or 'right'")
