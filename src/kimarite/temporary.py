from __future__ import annotations

from .models import BoutState, Card, GripState, Side, TemporaryInstance
from .catalog import card_by_name
from .prevention import prevent_negative_effect
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
    completed: bool = False,
) -> Card:
    fighter = state.fighter(side)
    if instance not in fighter.temporary_zone:
        raise ValueError("Temporary is not in that wrestler's Temporary Zone.")

    fighter.temporary_zone.remove(instance)
    card = instance.card

    # A disrupted Sidestep must release the shared Side-by-Side lock.
    # Without this, Push remains suppressed indefinitely after its card leaves.
    if card.name == "Sidestep" and state.side_by_side_owner is side:
        state.side_by_side_owner = None
        state.side_by_side_distance = 0
        state.log("Side-by-Side ends when Sidestep leaves the Temporary Zone.")

    if disrupted:
        if card.name in {
            "Attempt Two-Handed Grip",
            "Attempt Deep Outside Grip",
            "Attempt Deep Inside Grip",
        }:
            gain_momentum(state, state.opponent_side(side), 1)
        elif card.name == "Get Underneath":
            gain_momentum(state, state.opponent_side(side), 2)

    if card.name == "Salt Throw":
        state.log(f"{card.name} is exhausted instead of entering the Discard Pile.")
    else:
        fighter.discard_pile.append(card)
    if (completed and not disrupted
            and card.name in {"Henka", "Pull", "Sidestep", "Immovable", "Kannuki"}):
        fighter.successful_reversal_this_turn = True
        state.reversal_completions.append((side, card.name, state.turn_number))
        state.log(f"{card.name} successfully completes its Reversal.")
    state.temporary_outcomes.append(
        (side, card.name, "disrupted" if disrupted else "survived")
    )
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
        if name == "Salt Throw":
            if fighter.discard_pile:
                fighter.draw_pile.append(fighter.discard_pile.pop())
                state.log(f"{fighter.wrestler.name} recycles one card with Salt Throw.")
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
        elif name == "Tsuri":
            from .rules import effective_total_grip
            if fighter.power >= 5 and effective_total_grip(state, side) >= 2:
                gain_push(state, side, 3)
            else:
                gain_push(state, side, 1)
        elif name == "Yori":
            from .rules import effective_total_grip
            owner_grip = effective_total_grip(state, side)
            other_grip = effective_total_grip(state, state.opponent_side(side))
            gain_momentum(state, side, 3 if owner_grip > other_grip else 1)
        elif name == "Gaburi":
            if fighter.power > state.opponent(side).power:
                created = card_by_name("Yorikiri")
                fighter.kimarite_zone.append(created)
                state.log(f"{fighter.wrestler.name} creates Yorikiri with Gaburi.")
        elif name == "Hold Position":
            gain_momentum(state, side, 1)
            gain_power(state, side, 1)
        elif name == "Immovable":
            if not instance.opponent_gained_push_while_active:
                gain_momentum(state, side, 2)
        elif name == "Henka" and getattr(state, "r20_active", False):
            from .effects import draw_one
            draw_one(state, side)
        elif name == "Pull":
            state.momentum = -state.momentum
            state.log(f"{fighter.wrestler.name} reverses Momentum with surviving Pull.")
        elif name in {"Use the Tawara", "Give Ground"}:
            pass
        elif name == "Kannuki":
            opponent_side = state.opponent_side(side)
            if not prevent_negative_effect(
                state,
                opponent_side,
                source="Kannuki",
                description="reduce both Grips by 1 level",
            ):
                reduce_grip(state, opponent_side, hand="left")
                reduce_grip(state, opponent_side, hand="right")
        elif name == "Morozashi":
            gain_push(state, side, 1)
        elif name in {"Get Underneath", "Gain Left Grip", "Gain Right Grip", "Uwate", "Shitate"}:
            pass
        elif name == "Sidestep":
            distance = state.side_by_side_distance
            if state.side_by_side_owner is side:
                if state.momentum * state.sign(side) >= 0:
                    favorable = side
                else:
                    favorable = state.opponent_side(side)
                state.position = state.sign(favorable) * distance
                state.side_by_side_owner = None
                state.side_by_side_distance = 0
                state.log(
                    f"Sidestep survives; {state.fighter(favorable).wrestler.name} "
                    "takes the favorable orientation."
                )
        else:
            raise KeyError(f"No start-of-turn Temporary resolution for {name!r}.")

        remove_temporary(state, side, instance, disrupted=False, completed=True)
