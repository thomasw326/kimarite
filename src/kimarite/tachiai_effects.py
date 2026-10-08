from __future__ import annotations

from .effects import draw_one
from .models import BoutState, Side, Stat
from .prevention import prevent_negative_effect
from .rules import establish_grip, gain_momentum, gain_power, lose_power
from .tachiai import TachiaiComparison, apply_tachiai_power_push, apply_tachiai_push
from .temporary import add_temporary


PREPARED_TEMPORARY_TACHIAI = frozenset({"Headlong Charge", "Shiko Stomp"})


def _opponent_stats(comparison: TachiaiComparison, side: Side):
    return comparison.wrestler_b if side is Side.A else comparison.wrestler_a


def _activate_prebout_shiko(state: BoutState, side: Side) -> None:
    card = state.fighter(side).wrestler.prepared_tachiai_card
    if card.name == "Shiko Stomp":
        add_temporary(state, side, card, phase="pre-bout")


def _power_push_reduction(state: BoutState, comparison: TachiaiComparison) -> int:
    winner = comparison.power_winner
    if winner is None:
        return 0

    loser = state.opponent_side(winner)
    card = state.fighter(loser).wrestler.prepared_tachiai_card
    if card.name not in {"Hold Position", "Immovable", "Sidestep"}:
        return 0

    if prevent_negative_effect(
        state,
        winner,
        source=card.name,
        description="reduce Tachiai Push from the Power comparison",
    ):
        return 0
    return 1 if card.name == "Sidestep" else 2


def resolve_prepared_tachiai(state: BoutState, comparison: TachiaiComparison) -> None:
    """Resolve the original playtest wrestlers prepared Tachiai cards."""
    for side in (Side.A, Side.B):
        _activate_prebout_shiko(state, side)

    reduction = _power_push_reduction(state, comparison)
    power_winner, power_push = apply_tachiai_power_push(
        state, comparison, reduction=reduction
    )
    if state.winner is not None:
        return

    power_push_received = {
        Side.A: power_push if power_winner is Side.B else 0,
        Side.B: power_push if power_winner is Side.A else 0,
    }
    extra_push = {Side.A: 0, Side.B: 0}
    momentum_delta = {Side.A: 0, Side.B: 0}
    reset_position = False

    for side in (Side.A, Side.B):
        fighter = state.fighter(side)
        opponent_side = state.opponent_side(side)
        card = fighter.wrestler.prepared_tachiai_card
        name = card.name

        if name == "Headlong Charge":
            momentum_delta[side] += 1
            extra_push[side] += 1
            gain_power(state, side, 1)
            add_temporary(state, side, card, phase="tachiai")

        elif name == "Shiko Stomp":
            pass

        elif name == "Nodowa":
            gain_power(state, side, 2)
            if not prevent_negative_effect(
                state, opponent_side, source="Nodowa",
                description="look at 2 fewer cards for Technique",
            ):
                state.fighter(opponent_side).technique_look_adjustment -= 2

        elif name == "Harite":
            gain_power(state, side, 1)
            if not prevent_negative_effect(
                state, opponent_side, source="Harite",
                description="lose 1 Power",
            ):
                lose_power(state, opponent_side, 1)

        elif name == "Gain Left Grip":
            if comparison.advantage_for(side, Stat.TECHNIQUE) > 0:
                establish_grip(state, side, "left")

        elif name == "Gain Right Grip":
            if comparison.advantage_for(side, Stat.TECHNIQUE) > 0:
                establish_grip(state, side, "right")

        elif name == "Salt Throw":
            spirit_advantage = comparison.advantage_for(side, Stat.SPIRIT)
            for _ in range(max(0, spirit_advantage // 3)):
                draw_one(state, side)

        elif name == "Tsuppari":
            if comparison.advantage_for(side, Stat.POWER) >= 2:
                draw_one(state, side)

        elif name == "Stare Down":
            if comparison.advantage_for(side, Stat.POWER) > 0:
                extra_push[side] += 1
            if comparison.advantage_for(side, Stat.TECHNIQUE) > 0:
                fighter.technique_look_adjustment += 1
            if comparison.advantage_for(side, Stat.SPIRIT) > 0:
                momentum_delta[side] += 1

        elif name == "Power Water":
            pass

        elif name == "Belt Slap":
            spirit_advantage = comparison.advantage_for(side, Stat.SPIRIT)
            extra_push[side] += max(0, spirit_advantage // 3)

        elif name in {"Hold Position", "Immovable"}:
            pass

        elif name == "Henka":
            opponent = _opponent_stats(comparison, side)
            triggered = False
            if opponent.power >= 5:
                momentum_delta[side] += 1
                triggered = True
            if opponent.spirit >= 5:
                momentum_delta[side] += 1
                triggered = True
            if triggered:
                reset_position = True
            else:
                momentum_delta[opponent_side] += 3

        elif name == "Get Underneath":
            if power_push_received[side] <= 1:
                momentum_delta[side] += 1

        elif name == "Sidestep":
            if comparison.power_winner is opponent_side:
                raw_push = abs(comparison.power_advantage_a)
                if raw_push > 0:
                    momentum_delta[side] += 1

        elif name == "Give Ground":
            gain_power(state, side, 1)

        else:
            raise KeyError(f"Prepared Tachiai effect for {name!r} is not registered.")

    net_momentum = momentum_delta[Side.A] - momentum_delta[Side.B]
    if net_momentum > 0:
        gain_momentum(state, Side.A, net_momentum)
    elif net_momentum < 0:
        gain_momentum(state, Side.B, -net_momentum)

    net_push = extra_push[Side.A] - extra_push[Side.B]
    if net_push > 0:
        apply_tachiai_push(state, Side.A, net_push)
    elif net_push < 0:
        apply_tachiai_push(state, Side.B, -net_push)

    if state.winner is not None:
        return

    if reset_position:
        state.position = 0
        state.log("Henka resets the opening Position to 0.")

    for side in (Side.A, Side.B):
        card = state.fighter(side).wrestler.prepared_tachiai_card
        if card.name not in PREPARED_TEMPORARY_TACHIAI:
            state.fighter(side).draw_pile.append(card)
