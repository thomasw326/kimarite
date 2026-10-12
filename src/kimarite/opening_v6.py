"""V6 opening-hand preparation and commit-or-retain decisions.

An opt-in engine slice; older style simulations still use their legacy
starting Kimarite + prepared-card opening. This module deliberately stops
BEFORE card-specific Tachiai effects, opening Push, or Exchange turn order.
Those must be resolved by the next V6 integration step.

Controllers (human or AI) submit the same OpeningCommitment structure.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .models import BoutState, Card, FighterState, Side
from .tachiai import TachiaiComparison, TachiaiStats


@dataclass(frozen=True)
class OpeningCommitment:
    """Physical IDs of starting-hand cards committed during Tachiai.

    Cards not selected for commitment are retained in the Exchange hand.
    An empty tuple is legal: a wrestler can keep all three cards.
    """

    committed_card_ids: tuple[int, ...]


@dataclass(frozen=True)
class OpeningSideResult:
    committed: tuple[Card, ...]
    retained: tuple[Card, ...]
    kimarite_placed: tuple[Card, ...]
    exhausted: tuple[Card, ...]
    # Every non-Kimarite committed here is eligible for its Tachiai text;
    # a separate phase resolver decides whether it actually has such text.
    effects_to_resolve: tuple[Card, ...]


@dataclass(frozen=True)
class OpeningResolution:
    comparison: TachiaiComparison
    side_a: OpeningSideResult
    side_b: OpeningSideResult

    def for_side(self, side: Side) -> OpeningSideResult:
        return self.side_a if side is Side.A else self.side_b


def _check_ids(ids: Sequence[int], *, exactly: int | None = None) -> tuple[int, ...]:
    selected = tuple(ids)
    if exactly is not None and len(selected) != exactly:
        raise ValueError(f"Exactly {exactly} distinct opening cards are required.")
    if any(type(card_id) is not int for card_id in selected):
        raise ValueError("Opening selections must use physical integer card IDs.")
    if len(set(selected)) != len(selected):
        raise ValueError("An opening selection cannot use a physical card twice.")
    return selected


def assign_starting_hand(fighter: FighterState, card_ids: Sequence[int]) -> tuple[Card, ...]:
    """Move three designated cards out of the Draw Pile into the opening hand.

    No drawing, shuffling, or wrestlers' opening preferences are imposed here:
    a tournament controller can assign its three cards, while an AI builder
    can select its own three by affinity. This boundary is shared.
    """
    ids = _check_ids(card_ids, exactly=3)
    if fighter.hand or fighter.tachiai_committed:
        raise ValueError("Cannot assign an opening hand after it has begun.")
    if any(c.card_id in ids for c in fighter.kimarite_zone):
        raise ValueError("An opening card is already active in the Kimarite Zone.")
    by_id = {card.card_id: card for card in fighter.draw_pile}
    if len(by_id) != len(fighter.draw_pile):
        raise ValueError("Draw Pile contains duplicate physical card IDs.")
    if any(card_id not in by_id for card_id in ids):
        raise ValueError("Selected card must be in the wrestler's Draw Pile.")
    selected = tuple(by_id[card_id] for card_id in ids)
    selected_ids = set(ids)
    fighter.draw_pile = [
        card for card in fighter.draw_pile if card.card_id not in selected_ids
    ]
    fighter.hand = list(selected)
    return selected


def _validate_commitment(fighter: FighterState, decision: OpeningCommitment):
    if len(fighter.hand) != 3:
        raise ValueError("A new Tachiai requires exactly three cards in hand.")
    hand_ids = tuple(card.card_id for card in fighter.hand)
    if len(set(hand_ids)) != 3:
        raise ValueError("The starting hand has duplicate physical card IDs.")
    ids = _check_ids(decision.committed_card_ids)
    if any(card_id not in hand_ids for card_id in ids):
        raise ValueError("Cannot commit a card that is not in the starting hand.")
    chosen = set(ids)
    committed = tuple(c for c in fighter.hand if c.card_id in chosen)
    retained = tuple(c for c in fighter.hand if c.card_id not in chosen)
    return committed, retained


def _totals(fighter: FighterState, committed: tuple[Card, ...]) -> TachiaiStats:
    # Preserve the existing baseline (+1 to each of Power, Technique, Spirit).
    # Unlike prepared_stats(), do NOT automatically count a starting Kimarite
    # or a prepared card. Only the cards actually committed provide orbs.
    wrestler = fighter.wrestler
    return TachiaiStats(
        power=wrestler.base_power + 1 + sum(c.power for c in committed),
        technique=wrestler.base_technique + 1 + sum(c.technique for c in committed),
        spirit=wrestler.base_spirit + 1 + sum(c.spirit for c in committed),
    )


def commit_opening(
    state: BoutState,
    choice_a: OpeningCommitment,
    choice_b: OpeningCommitment,
) -> OpeningResolution:
    """Apply both simultaneous Tachiai commitments after validating BOTH.

    Side A/B cannot inspect the other's selection through this function before
    submitting a choice. Any invalid choice leaves BOTH sides unchanged.

    Non-Kimarite committed cards are out of the bout in exhausted_cards.
    Committed Kimarite remain accessible in kimarite_zone for card interactions
    and later win checks; committing never itself triggers a finishing check.
    Original cards also appear in inert tachiai_committed history.

    The returned comparison is ready for later Tachiai-effect resolution.
    DO NOT start the Exchange from this function: effects and Push are pending.
    """
    if state.v6_opening_committed:
        raise ValueError("This bout has already resolved its opening commitment.")
    prepared_a = _validate_commitment(state.fighter_a, choice_a)
    prepared_b = _validate_commitment(state.fighter_b, choice_b)

    # Reject any pre-existing active Kimarite with the same physical identity.
    for fighter, (committed, _) in (
        (state.fighter_a, prepared_a), (state.fighter_b, prepared_b)
    ):
        live_ids = {c.card_id for c in fighter.kimarite_zone}
        if any(c.card_id in live_ids for c in committed):
            raise ValueError("A card cannot be both active and in the starting hand.")

    def apply(fighter: FighterState, selected) -> OpeningSideResult:
        committed, retained = selected
        kimarite = tuple(c for c in committed if c.is_kimarite)
        exhausted = tuple(c for c in committed if not c.is_kimarite)
        fighter.hand = list(retained)
        fighter.tachiai_committed.extend(committed)
        fighter.exhausted_cards.extend(exhausted)
        fighter.kimarite_zone.extend(kimarite)
        return OpeningSideResult(
            committed=committed,
            retained=retained,
            kimarite_placed=kimarite,
            exhausted=exhausted,
            effects_to_resolve=exhausted,
        )

    # Calculate immutable snapshots before moving the physical cards.
    stats_a = _totals(state.fighter_a, prepared_a[0])
    stats_b = _totals(state.fighter_b, prepared_b[0])
    comparison = TachiaiComparison(
        wrestler_a=stats_a,
        wrestler_b=stats_b,
        power_advantage_a=stats_a.power - stats_b.power,
        technique_advantage_a=stats_a.technique - stats_b.technique,
        spirit_advantage_a=stats_a.spirit - stats_b.spirit,
    )
    result_a = apply(state.fighter_a, prepared_a)
    result_b = apply(state.fighter_b, prepared_b)
    state.v6_opening_committed = True
    state.log(
        f"Tachiai commitment: {state.fighter_a.wrestler.name} committed "
        f"{len(result_a.committed)}; {state.fighter_b.wrestler.name} committed "
        f"{len(result_b.committed)}."
    )
    return OpeningResolution(comparison=comparison, side_a=result_a, side_b=result_b)


def first_exchange_side_v6(
    opening: OpeningResolution, wrestler_a, wrestler_b,
) -> Side:
    """V6 opening priority: Spirit, then Power, Technique, and ranking.

    Legacy first_exchange_side() used Technique first. The V6 order matches
    the current game-design document while leaving B7 simulations untouched.
    """
    diff = opening.comparison
    for value in (
        diff.spirit_advantage_a,
        diff.power_advantage_a,
        diff.technique_advantage_a,
    ):
        if value > 0:
            return Side.A
        if value < 0:
            return Side.B
    if wrestler_a.ranking is not None and wrestler_b.ranking is not None:
        if wrestler_a.ranking < wrestler_b.ranking:
            return Side.A
        if wrestler_b.ranking < wrestler_a.ranking:
            return Side.B
    raise ValueError("Opening priority tied; distinct wrestler ranks are required.")
