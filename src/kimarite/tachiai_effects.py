from __future__ import annotations

from .effects import draw_one, give_opponent_kimarite, resolve_exchange_effect, EffectContext
from .models import BoutState, Side, Stat, Card
from .prevention import prevent_negative_effect
from .rules import establish_grip, gain_momentum, gain_power, lose_power
from .tachiai import TachiaiComparison, TachiaiStats, apply_tachiai_power_push, apply_tachiai_push
from .temporary import add_temporary


PREPARED_TEMPORARY_TACHIAI = frozenset({"Shiko Stomp", "Salt Throw"})
REVEAL_FAMILY = frozenset({"Oshi", "Tsuki"})


def _reveal_tachiai_orbs(state: BoutState, comparison: TachiaiComparison) -> None:
    extras = {Side.A: [0, 0, 0], Side.B: [0, 0, 0]}
    for side in (Side.A, Side.B):
        fighter = state.fighter(side)
        if fighter.wrestler.prepared_tachiai_card.name not in REVEAL_FAMILY:
            continue
        while fighter.draw_pile:
            card = fighter.draw_pile.pop(0)
            extras[side][0] += card.power
            extras[side][1] += card.technique
            extras[side][2] += card.spirit
            fighter.discard_pile.append(card)
            state.log(f"{fighter.wrestler.name} reveals {card.name} for Tachiai orbs.")
            if card.name not in REVEAL_FAMILY:
                break
    a, b = extras[Side.A], extras[Side.B]
    old_a, old_b = comparison.wrestler_a, comparison.wrestler_b
    new_a = TachiaiStats(old_a.power+a[0], old_a.technique+a[1], old_a.spirit+a[2])
    new_b = TachiaiStats(old_b.power+b[0], old_b.technique+b[1], old_b.spirit+b[2])
    object.__setattr__(comparison, "wrestler_a", new_a)
    object.__setattr__(comparison, "wrestler_b", new_b)
    object.__setattr__(comparison, "power_advantage_a", new_a.power-new_b.power)
    object.__setattr__(comparison, "technique_advantage_a", new_a.technique-new_b.technique)
    object.__setattr__(comparison, "spirit_advantage_a", new_a.spirit-new_b.spirit)


def _shuffle_generated(state: BoutState, side: Side, cards: list[Card]) -> None:
    import hashlib
    import random
    fighter = state.fighter(side)
    signature = repr((state.turn_number, side.value,
                      tuple((c.card_id, c.name) for c in fighter.draw_pile),
                      tuple((s.value, i) for s, i in state.card_play_ids)))
    seed = int.from_bytes(hashlib.sha256(signature.encode()).digest()[:8], "big")
    fighter.draw_pile.extend(cards)
    random.Random(seed).shuffle(fighter.draw_pile)



def _opponent_stats(comparison: TachiaiComparison, side: Side):
    return comparison.wrestler_b if side is Side.A else comparison.wrestler_a


def _activate_prebout_shiko(state: BoutState, side: Side) -> None:
    card = state.fighter(side).wrestler.prepared_tachiai_card
    if card.name == "Shiko Stomp":
        add_temporary(state, side, card, phase="pre-bout")


def _power_push_reduction(state: BoutState, comparison: TachiaiComparison) -> int:
    winner = comparison.spirit_winner
    if winner is None:
        return 0

    loser = state.opponent_side(winner)
    card = state.fighter(loser).wrestler.prepared_tachiai_card
    if card.name not in {"Hold Position", "Immovable", "Sidestep", "Give Ground"}:
        return 0

    if prevent_negative_effect(
        state,
        winner,
        source=card.name,
        description="reduce Tachiai Push from the Spirit comparison",
    ):
        return 0
    return 1 if card.name in {"Sidestep", "Give Ground"} else 2


def resolve_prepared_tachiai(
    state: BoutState,
    comparison: TachiaiComparison,
    *,
    sacrifice_choices: dict[Side, int | None] | None = None,
) -> None:
    """Resolve prepared Tachiai cards, including cards without a Tachiai-specific effect."""
    for side in (Side.A, Side.B):
        _activate_prebout_shiko(state, side)
    _reveal_tachiai_orbs(state, comparison)
    state.tachiai_spirit_advantage_a = comparison.spirit_advantage_a

    # Resolve Tachiai Power modifiers before Spirit Push resistance.
    for side in (Side.A, Side.B):
        name = state.fighter(side).wrestler.prepared_tachiai_card.name
        if name == "Nodowa":
            gain_power(state, side, 2)
        elif name == "Harite":
            gain_power(state, side, 1)
            opponent_side = state.opponent_side(side)
            if not prevent_negative_effect(
                state, opponent_side, source="Harite",
                description="lose 1 Power",
            ):
                lose_power(state, opponent_side, 1)

    reduction = _power_push_reduction(state, comparison)
    spirit_winner, spirit_push = apply_tachiai_power_push(
        state, comparison, reduction=reduction
    )
    if state.winner is not None:
        return

    power_push_received = {
        Side.A: spirit_push if spirit_winner is Side.B else 0,
        Side.B: spirit_push if spirit_winner is Side.A else 0,
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
            # An omitted choice means decline, never sacrifice automatically.
            choice = (sacrifice_choices or {}).get(side)
            if choice is not None:
                if type(choice) is not int or not 0 <= choice < len(fighter.kimarite_zone):
                    raise ValueError("Invalid Headlong Charge sacrifice choice")
                sacrificed = fighter.kimarite_zone.pop(choice)
                fighter.discard_pile.append(sacrificed)
                state.log(f"{fighter.wrestler.name} sacrifices {sacrificed.name}.")
                momentum_delta[side] += 1
                extra_push[side] += 1

        elif name == "Shiko Stomp":
            pass

        elif name == "Nodowa":
            if not prevent_negative_effect(
                state, opponent_side, source="Nodowa",
                description="look at 2 fewer cards for Technique",
            ):
                state.fighter(opponent_side).technique_look_adjustment -= 2

        elif name == "Harite":
            pass

        elif name == "Gain Left Grip":
            if comparison.advantage_for(side, Stat.TECHNIQUE) > 0:
                establish_grip(state, side, "left")

        elif name == "Gain Right Grip":
            if comparison.advantage_for(side, Stat.TECHNIQUE) > 0:
                establish_grip(state, side, "right")

        elif name == "Salt Throw":
            resolve_exchange_effect(state, side, card, EffectContext(comparison=comparison))

        elif name == "Tsuppari":
            _shuffle_generated(state, side, [
                Card(20001, "Oshi", 0, 0, 1),
                Card(20002, "Tsuki", 1, 0, 0),
                Card(20003, "Shove", 2, 0, 0),
            ])

        elif name == "Explosive Step — Fumikomi":
            if comparison.spirit_winner is side:
                extra_push[side] += 1

        elif name == "Shove":
            # Applied after net opening push below, to preserve ordering.
            extra_push[side] += 1

        elif name == "Stare Down":
            if comparison.advantage_for(side, Stat.POWER) > 0:
                extra_push[side] += 1
            if comparison.advantage_for(side, Stat.TECHNIQUE) > 0:
                fighter.technique_keep_adjustment += 1
            if comparison.advantage_for(side, Stat.SPIRIT) > 0:
                momentum_delta[side] += 1

        elif name == "Belt Slap":
            pass

        elif name in {"Hold Position", "Immovable"}:
            pass

        elif name == "Henka":
            if (
                comparison.wrestler_a.technique if side is Side.A else comparison.wrestler_b.technique
            ) > _opponent_stats(comparison, side).spirit:
                reset_position = True

        elif name == "Get Underneath":
            momentum_delta[side] += 1
            extra_push[side] += 1
            give_opponent_kimarite(state, side, name)

        elif name == "Sidestep":
            if comparison.spirit_winner is opponent_side:
                raw_push = abs(comparison.spirit_advantage_a)
                if raw_push > 0:
                    momentum_delta[side] += 1



        else:
            # All legal prepared cards contribute their printed orbs through
            # compare_tachiai. Cards with no Tachiai text have no additional
            # opening effect; their Exchange effect is NOT triggered here.
            state.log(f"{name} has no additional Tachiai effect.")

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

    for side in (Side.A, Side.B):
        if (state.fighter(side).wrestler.prepared_tachiai_card.name == "Shove"
                and state.position * state.sign(side) == 3):
            state.win_source = "Shove Tachiai"
            state.declare_winner(side, "Shove")
            return

    if reset_position:
        state.position = 0
        state.log("Henka resets the opening Position to 0.")

    # BEGIN APPROVED MILL/RECYCLE V1
    # Prepared explosive cards pay their Tachiai mill cost after opening effects.
    for side in (Side.A, Side.B):
        name = state.fighter(side).wrestler.prepared_tachiai_card.name
        if name in {"Headlong Charge", "Explosive Step — Fumikomi"}:
            from .effects import mill_cards
            mill_cards(state, side, 2)
    # END APPROVED MILL/RECYCLE V1

    for side in (Side.A, Side.B):
        card = state.fighter(side).wrestler.prepared_tachiai_card
        if card.name not in PREPARED_TEMPORARY_TACHIAI:
            state.fighter(side).draw_pile.append(card)
