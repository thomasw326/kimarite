from __future__ import annotations

from .models import BoutState, Card, GripState, Side, TemporaryInstance
from .rules import establish_grip, gain_momentum, gain_power, gain_push, reduce_grip


def add_temporary(
    state: BoutState,
    side: Side,
    card: Card,
    *,
    phase: str,
) -> TemporaryInstance:
    instance = TemporaryInstance(
        card=card,
        entered_turn=state.turn_number,
        entered_phase=phase,
    )
    state.fighter(side).temporary_zone.append(instance)
    state.log(f"{card.name} enters {state.fighter(side).wrestler.name}'s Temporary Zone.")
    return instance


def find_temporary(
    state: BoutState,
    side: Side,
    card_name: str,
) -> TemporaryInstance | None:
    for instance in state.fighter(side).temporary_zone:
        if instance.card.name == card_name:
            return instance
    return None


def remove_temporary(
    state: BoutState,
    side: Side,
    instance: TemporaryInstance,
    *,
    disrupted: bool,
) -> Card:
    fighter = state.fighter(side)
    if instance not in fighter.temporary_zone:
        raise ValueError("Temporary is not in that wrestler's Temporary Zone.")

    fighter.temporary_zone.remove(instance)
    card = instance.card

    if disrupted:
        if card.name == "Headlong Charge":
            gain_momentum(state, state.opponent_side(side), 3)
        elif card.name in {
            "Attempt Two-Handed Grip",
            "Attempt Deep Outside Grip",
            "Attempt Deep Inside Grip",
        }:
            gain_momentum(state, state.opponent_side(side), 1)
        elif card.name == "Get Underneath":
            gain_momentum(state, state.opponent_side(side), 2)

    fighter.discard_pile.append(card)
    state.log(
        f"{card.name} leaves {fighter.wrestler.name}'s Temporary Zone"
        + (" after disruption." if disrupted else ".")
    )
    return card


def resolve_start_of_turn_temporaries(state: BoutState, side: Side) -> None:
    """Resolve the owner's surviving Temporary cards in zone order."""
    fighter = state.fighter(side)

    for instance in list(fighter.temporary_zone):
        name = instance.card.name

        # Shiko Stomp explicitly does not leave at the start of the owner's turn.
        if name == "Shiko Stomp":
            continue

        if name == "Attempt Two-Handed Grip":
            establish_grip(state, side, "left")
            establish_grip(state, side, "right")
        elif name == "Attempt Deep Outside Grip":
            fighter.left_grip = GripState.DEEP
            state.log(f"{fighter.wrestler.name}'s Left Grip becomes DEEP.")
        elif name == "Attempt Deep Inside Grip":
            fighter.right_grip = GripState.DEEP
            state.log(f"{fighter.wrestler.name}'s Right Grip becomes DEEP.")
        elif name == "Hold Position":
            gain_momentum(state, side, 1)
            gain_power(state, side, 1)
        elif name == "Immovable":
            if not instance.opponent_gained_push_while_active:
                gain_momentum(state, side, 2)
        elif name == "Pull":
            state.momentum *= -1
            state.log(f"{fighter.wrestler.name} reverses Momentum.")
        elif name == "Use the Tawara":
            pass
        elif name == "Kannuki":
            opponent_side = state.opponent_side(side)
            reduce_grip(state, opponent_side, hand="left")
            reduce_grip(state, opponent_side, hand="right")
        elif name == "Morozashi":
            gain_momentum(state, side, 1)
            gain_push(state, side, 1)
        elif name in {"Headlong Charge", "Get Underneath"}:
            pass
        elif name == "Sidestep":
            raise NotImplementedError("Side-by-Side resolution is not wired yet.")
        else:
            raise KeyError(f"No start-of-turn Temporary resolution for {name!r}.")

        remove_temporary(state, side, instance, disrupted=False)
