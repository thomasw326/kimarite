from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from statistics import mean
from typing import Iterable

from .models import Side
from .setup import BoutConfig, FighterConfig
from .simulate import run_bout


@dataclass(frozen=True)
class BoutRecord:
    wrestler_a: str
    wrestler_b: str
    seed_a: int
    seed_b: int
    completed: bool
    winner: str | None
    win_method: str | None
    turns: int
    cards_played_a: tuple[str, ...]
    cards_played_b: tuple[str, ...]
    unsupported_reason: str | None = None

    @property
    def winning_cards(self) -> tuple[str, ...]:
        if self.winner == self.wrestler_a:
            return self.cards_played_a
        if self.winner == self.wrestler_b:
            return self.cards_played_b
        return ()


@dataclass(frozen=True)
class SeriesSummary:
    bouts: int
    completed_bouts: int
    wins: dict[str, int]
    win_methods: dict[str, int]
    winning_card_uses: dict[str, int]
    average_turns: float


def run_series(
    wrestler_a: str,
    wrestler_b: str,
    seed_pairs: Iterable[tuple[int, int]],
    *,
    exclusions_a: frozenset[int] = frozenset(),
    exclusions_b: frozenset[int] = frozenset(),
    ranking_a: int | None = 1,
    ranking_b: int | None = 2,
    max_turns: int = 100,
) -> list[BoutRecord]:
    records: list[BoutRecord] = []

    for seed_a, seed_b in seed_pairs:
        result = run_bout(
            BoutConfig(
                FighterConfig(
                    wrestler_a,
                    seed_a,
                    exclusions_a,
                    ranking=ranking_a,
                ),
                FighterConfig(
                    wrestler_b,
                    seed_b,
                    exclusions_b,
                    ranking=ranking_b,
                ),
            ),
            max_turns=max_turns,
        )
        state = result.state

        winner: str | None = None
        if state.winner is Side.A:
            winner = wrestler_a
        elif state.winner is Side.B:
            winner = wrestler_b

        records.append(
            BoutRecord(
                wrestler_a=wrestler_a,
                wrestler_b=wrestler_b,
                seed_a=seed_a,
                seed_b=seed_b,
                completed=result.completed,
                winner=winner,
                win_method=state.win_method,
                turns=result.turns,
                cards_played_a=tuple(
                    name for side, name in state.card_plays if side is Side.A
                ),
                cards_played_b=tuple(
                    name for side, name in state.card_plays if side is Side.B
                ),
                unsupported_reason=result.unsupported_reason,
            )
        )

    return records


def summarize_series(records: list[BoutRecord]) -> SeriesSummary:
    completed = [record for record in records if record.completed]
    wins = Counter(record.winner for record in completed if record.winner)
    methods = Counter(
        record.win_method for record in completed if record.win_method
    )
    winning_cards = Counter(
        card
        for record in completed
        for card in record.winning_cards
    )

    return SeriesSummary(
        bouts=len(records),
        completed_bouts=len(completed),
        wins=dict(wins),
        win_methods=dict(methods),
        winning_card_uses=dict(winning_cards),
        average_turns=mean(record.turns for record in completed)
        if completed
        else 0.0,
    )


def deterministic_seed_pairs(
    count: int,
    *,
    start_a: int = 1,
    start_b: int = 100_001,
) -> list[tuple[int, int]]:
    if count < 0:
        raise ValueError("count must be non-negative")
    return [
        (start_a + index, start_b + index)
        for index in range(count)
    ]
