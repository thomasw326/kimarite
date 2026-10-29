from __future__ import annotations

from collections.abc import Callable

from .kimarite import satisfied_kimarite
from .models import BoutState, Card, Side, Stat
from .rules import effective_total_grip, gain_momentum, grip_benefits_suppressed
from .selection import ai_look_keep, keep_and_bottom, look_from_top
from .tachiai import TachiaiComparison, technique_access
from .temporary import resolve_start_of_turn_temporaries


class TemporaryResolutionRequired(RuntimeError):
    pass


TemporaryStartResolver = Callable[[BoutState, Side], None]
KimariteChoiceResolver = Callable[[BoutState, Side, list[Card]], Card]
CardAccessChooser = Callable[[list[Card], int], list[Card]]


def _choose_card_access(fighter, look: int, keep: int, chooser: CardAccessChooser | None) -> list[Card]:
    if chooser is None:
        return ai_look_keep(fighter, look, keep)
    looked = look_from_top(fighter, look)
    required = min(keep, len(looked))
    selected = chooser(looked, required)
    if len(selected) != required:
        raise ValueError(f"Must keep exactly {required} card(s).")
    keep_and_bottom(fighter, looked, selected)
    return selected


def prepare_exchange_deck(state: BoutState, side: Side) -> None:
    """Put the prepared Tachiai card on the bottom after Tachiai resolution."""
    fighter = state.fighter(side)
    fighter.draw_pile.append(fighter.wrestler.prepared_tachiai_card)


def apply_initial_power(state: BoutState, comparison: TachiaiComparison) -> None:
    """Power persists into the Exchange at the prepared Tachiai total."""
    state.fighter_a.power = comparison.wrestler_a.power
    state.fighter_b.power = comparison.wrestler_b.power


def resolve_first_turn_spirit_reward(
    state: BoutState,
    side: Side,
    comparison: TachiaiComparison,
) -> tuple[int, int]:
    """Resolve first-turn Spirit before the start-of-turn Kimarite check."""
    fighter = state.fighter(side)
    if not fighter.spirit_reward_pending:
        return (0, 0)

    advantage = comparison.advantage_for(side, Stat.SPIRIT)
    momentum, bonus_turns = (0, 0)  # V4.4: Spirit generates Tachiai Push instead.
    fighter.spirit_reward_pending = False
    fighter.bonus_turns_queued += bonus_turns
    if momentum:
        gain_momentum(state, side, momentum)
    return (momentum, bonus_turns)


def first_turn_card_access(
    state: BoutState,
    side: Side,
    comparison: TachiaiComparison,
    *, choose_cards: CardAccessChooser | None = None,
) -> list[Card]:
    fighter = state.fighter(side)
    if not fighter.technique_reward_pending:
        return []

    # The first-turn Technique result IS the first hand/card access for that turn.
    # It does not stack with the ordinary 2 + Grip Exchange selection.
    advantage = comparison.advantage_for(side, Stat.TECHNIQUE)
    look, keep = technique_access(advantage)
    keep += fighter.technique_keep_adjustment
    look = max(2, keep, look + fighter.technique_look_adjustment)
    fighter.technique_reward_pending = False
    return _choose_card_access(fighter, look, keep, choose_cards)


def normal_turn_card_access(
    state: BoutState, side: Side, *, choose_cards: CardAccessChooser | None = None
) -> list[Card]:
    fighter = state.fighter(side)
    look = 2 + effective_total_grip(state, side, consume_prevention=True)
    return _choose_card_access(fighter, look, 2, choose_cards)


def resolve_turn_card_access(
    state: BoutState,
    side: Side,
    comparison: TachiaiComparison,
    *, choose_cards: CardAccessChooser | None = None,
) -> list[Card]:
    fighter = state.fighter(side)
    if fighter.first_exchange_turn:
        cards = first_turn_card_access(state, side, comparison, choose_cards=choose_cards)
        fighter.first_exchange_turn = False
        return cards
    return normal_turn_card_access(state, side, choose_cards=choose_cards)


def apply_start_of_turn_exhaustion(state: BoutState, side: Side) -> None:
    """Apply the current start-of-turn Exhaustion rule once for this turn."""
    fighter = state.fighter(side)

    if not fighter.draw_pile:
        state.declare_winner(state.opponent_side(side), "Exhaustion")
        return

    # A nonzero Grip total that ties or leads the opponent protects against
    # discard-pile Power fatigue. A 0-0 tie protects neither wrestler.
    own_grip = effective_total_grip(state, side)
    other_grip = effective_total_grip(state, state.opponent_side(side))
    grip_protected = own_grip > 0 and own_grip >= other_grip
    if len(fighter.discard_pile) >= 7 and not grip_protected:
        fighter.power -= 1
        state.log(f"{fighter.wrestler.name} loses 1 Power to Exhaustion.")

    if fighter.power < 0:
        state.declare_winner(state.opponent_side(side), "Power")


def reset_turn_events(state: BoutState, side: Side) -> None:
    fighter = state.fighter(side)
    fighter.plays_remaining = 2
    fighter.cards_played_this_turn = 0
    fighter.played_this_turn.clear()
    fighter.lost_position_this_turn = False
    state.position_loss_events = [e for e in state.position_loss_events if e[0] is not side]
    fighter.opponent_grip_reduced_this_turn = False
    fighter.gained_push_this_turn = False
    fighter.gained_momentum_this_turn = False
    fighter.successful_reversal_this_turn = False


def check_kimarite_zone(
    state: BoutState,
    side: Side,
    *,
    choose_kimarite: KimariteChoiceResolver | None = None,
) -> Card | None:
    """Resolve a Kimarite win.

    Satisfied cards are returned in Kimarite Zone order, so the default is the
    earliest-played satisfied Kimarite. A chooser may override that selection
    when a later reward layer determines the alternatives have meaningfully
    different win rewards.
    """
    cards = satisfied_kimarite(state, side)
    if not cards:
        return None

    if choose_kimarite is None or len(cards) == 1:
        card = cards[0]
    else:
        card = choose_kimarite(state, side, cards)
        if card not in cards:
            raise ValueError("Kimarite chooser must return one of the satisfied cards.")

    grip_win_cards = {
        "Yorikiri", "Yoritaoshi", "Uwatenage",
        "Hikiotoshi", "Tsuridashi", "Abisetaoshi",
    }
    if card.name in grip_win_cards and grip_benefits_suppressed(state, side):
        effective_total_grip(state, side, consume_prevention=True)

    if card.name == "Katasukashi":
        sources = [source for event_side, turn, source, amount in state.position_loss_events
                   if event_side is side and turn == state.turn_number]
        state.katasukashi_win_sources = list(dict.fromkeys(sources)) or ["unknown"]
    if getattr(state, "b11_explain_wins", False) and card.name == "Sukuinage":
        grip = state.fighter(side).total_grip
        momentum = state.momentum * state.sign(side)
        hand_advantage = len(state.fighter(side).hand) - len(state.opponent(side).hand)
        state.log(
            f"Sukuinage conditions satisfied: Grip {grip} (required 0); "
            f"Momentum advantage {momentum} (required ≥2); "
            f"Hand advantage {hand_advantage} (required ≥4)."
        )
    if getattr(state, "b11_explain_wins", False):
        winner = state.fighter(side)
        opponent = state.opponent(side)
        from .b11_victory_checks import victory_checks
        from .b10_card_info import card_info
        details = card_info(card)
        import re
        description = details.get("description", "")
        win_text = re.search(r"Win:\s*(.*?)(?=\s*On play:|$)", description)
        state.b11_victory_details = {
            "checks": victory_checks(state, side, card.name),
            "kimarite": card.name,
            "requirement_text": win_text.group(1).strip() if win_text else description,
            "grip": winner.total_grip,
            "effective_grip": effective_total_grip(state, side),
            "power": winner.power,
            "momentum_advantage": state.momentum * state.sign(side),
            "position_advantage": state.position * state.sign(side),
            "hand_advantage": len(winner.hand) - len(opponent.hand),
            "turn": state.turn_number,
        }
    state.win_source = "kimarite"
    state.winning_kimarite_card_id = card.card_id
    state.declare_winner(side, card.name)
    return card


def start_exchange_turn(
    state: BoutState,
    side: Side,
    comparison: TachiaiComparison,
    *,
    resolve_temporary_start: TemporaryStartResolver | None = None,
    choose_kimarite: KimariteChoiceResolver | None = None,
    choose_cards: CardAccessChooser | None = None,
) -> list[Card]:
    """Run the fixed start-of-turn sequence through card access.

    Order:
    1. reset turn counters/events
    2. first-turn Spirit reward (first Exchange turn only)
    3. start-of-turn Kimarite check
    4. start-of-turn Temporary effects
    5. Exhaustion / negative-Power loss
    6. first-turn Technique access OR normal 2 + Grip access

    Temporary-zone behavior is card-specific, so a resolver is required when
    cards are present rather than silently guessing duration/resolution.
    """
    state.active_side = side
    state.turn_number += 1
    state.fighter(side).turns_started += 1
    # Preserve the opponent's prevented/reduced Grip attempt until Tottari's
    # start-of-turn check; ordinary turn counters still reset immediately.
    grip_event_for_tottari = state.fighter(side).opponent_grip_reduced_this_turn
    reset_turn_events(state, side)
    state.fighter(side).opponent_grip_reduced_this_turn = grip_event_for_tottari

    fighter = state.fighter(side)
    if fighter.first_exchange_turn:
        resolve_first_turn_spirit_reward(state, side, comparison)
        if state.winner is not None:
            return []

    # Only R20 reverses the legacy ordering: completed Reversal Temporaries
    # must resolve and naturally discard BEFORE the starting Kimarite check.
    if getattr(state, "r20_active", False) and fighter.temporary_zone:
        if resolve_temporary_start is None:
            resolve_start_of_turn_temporaries(state, side)
        else:
            resolve_temporary_start(state, side)
        if state.winner is not None:
            return []

    check_kimarite_zone(state, side, choose_kimarite=choose_kimarite)
    # Do not carry last turn's event into this turn's end-of-turn check.
    fighter.opponent_grip_reduced_this_turn = False
    if state.winner is not None:
        return []

    if not getattr(state, "r20_active", False) and fighter.temporary_zone:
        if resolve_temporary_start is None:
            resolve_start_of_turn_temporaries(state, side)
        else:
            resolve_temporary_start(state, side)
        if state.winner is not None:
            return []

    # Surviving Reversal Temporaries can complete in normal V5.1 bouts.
    # They resolve after the legacy opening Kimarite check, so check again
    # before exhaustion or drawing; otherwise all Reversal finishers are inert.
    if fighter.successful_reversal_this_turn:
        check_kimarite_zone(state, side, choose_kimarite=choose_kimarite)
        if state.winner is not None:
            return []

    apply_start_of_turn_exhaustion(state, side)
    if state.winner is not None:
        return []

    return resolve_turn_card_access(state, side, comparison, choose_cards=choose_cards)


def end_exchange_turn(
    state: BoutState,
    side: Side,
    *,
    choose_kimarite: KimariteChoiceResolver | None = None,
) -> Side | None:
    """Check Kimarite, then schedule the next wrestler."""
    check_kimarite_zone(state, side, choose_kimarite=choose_kimarite)
    if state.winner is not None:
        return None

    fighter = state.fighter(side)
    # B9 Unstable lasts through the affected fighter's turn, then clears.
    if fighter.unstable and fighter.turns_started >= fighter.unstable_recovery_turn:
        fighter.unstable = False
        fighter.unstable_recovery_turn = 0
        state.log(f"{fighter.wrestler.name} regains Stability after their turn.")
    if fighter.bonus_turns_queued > 0:
        fighter.bonus_turns_queued -= 1
        next_side = side
    else:
        next_side = state.opponent_side(side)

    state.active_side = next_side
    return next_side
