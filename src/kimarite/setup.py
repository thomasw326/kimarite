from __future__ import annotations

from dataclasses import dataclass, field

from .catalog import PLAYTEST_WRESTLERS
from .deck import build_seeded_deck
from .models import BoutState, FighterState, Side
from .tachiai import TachiaiComparison, compare_tachiai, first_exchange_side
from .tachiai_effects import resolve_prepared_tachiai
from .turns import apply_initial_power


@dataclass(frozen=True)
class FighterConfig:
    wrestler_name: str
    seed: int
    excluded_ids: frozenset[int] = field(default_factory=frozenset)
    ranking: int | None = None


@dataclass(frozen=True)
class BoutConfig:
    fighter_a: FighterConfig
    fighter_b: FighterConfig


@dataclass(frozen=True)
class PreparedBout:
    state: BoutState
    comparison: TachiaiComparison


def create_prepared_bout(config: BoutConfig) -> PreparedBout:
    template_a = PLAYTEST_WRESTLERS[config.fighter_a.wrestler_name]
    template_b = PLAYTEST_WRESTLERS[config.fighter_b.wrestler_name]
    wrestler_a = template_a.build(ranking=config.fighter_a.ranking)
    wrestler_b = template_b.build(ranking=config.fighter_b.ranking)

    deck_a = build_seeded_deck(
        wrestler_a,
        config.fighter_a.seed,
        set(config.fighter_a.excluded_ids),
    )
    deck_b = build_seeded_deck(
        wrestler_b,
        config.fighter_b.seed,
        set(config.fighter_b.excluded_ids),
    )

    state = BoutState(
        fighter_a=FighterState(
            wrestler_a,
            draw_pile=deck_a,
            kimarite_zone=[wrestler_a.starting_kimarite],
        ),
        fighter_b=FighterState(
            wrestler_b,
            draw_pile=deck_b,
            kimarite_zone=[wrestler_b.starting_kimarite],
        ),
    )

    comparison = compare_tachiai(wrestler_a, wrestler_b)
    apply_initial_power(state, comparison)
    resolve_prepared_tachiai(state, comparison)

    if state.winner is None:
        state.active_side = first_exchange_side(comparison, wrestler_a, wrestler_b)

    return PreparedBout(state=state, comparison=comparison)
