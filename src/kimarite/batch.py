from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from statistics import mean
from typing import Iterable

from .exclusions import exclusions_for_difficulty
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


@dataclass(frozen=True)
class Standing:
    wrestler: str
    bouts: int
    completed_bouts: int
    wins: int
    losses: int
    win_rate: float


def run_round_robin(
    wrestler_names: Iterable[str],
    *,
    bouts_per_orientation: int = 1,
    exclusions_by_wrestler: dict[str, frozenset[int]] | None = None,
    max_turns: int = 100,
    seed_start: int = 1,
) -> list[BoutRecord]:
    names = list(wrestler_names)
    if len(set(names)) != len(names):
        raise ValueError("wrestler_names must be unique")
    if bouts_per_orientation < 1:
        raise ValueError("bouts_per_orientation must be at least 1")

    exclusions_by_wrestler = exclusions_by_wrestler or {}
    records: list[BoutRecord] = []
    seed_cursor = seed_start

    for i, wrestler_a in enumerate(names):
        for wrestler_b in names[i + 1:]:
            for _ in range(bouts_per_orientation):
                seed_a = seed_cursor
                seed_b = seed_cursor + 100_000
                seed_cursor += 1

                records.extend(
                    run_series(
                        wrestler_a,
                        wrestler_b,
                        [(seed_a, seed_b)],
                        exclusions_a=exclusions_by_wrestler.get(
                            wrestler_a, frozenset()
                        ),
                        exclusions_b=exclusions_by_wrestler.get(
                            wrestler_b, frozenset()
                        ),
                        ranking_a=1,
                        ranking_b=2,
                        max_turns=max_turns,
                    )
                )

                # Mirror the matchup so Side/ranking tie-breaks are balanced
                # across the aggregate rather than favoring the first name.
                records.extend(
                    run_series(
                        wrestler_b,
                        wrestler_a,
                        [(seed_b, seed_a)],
                        exclusions_a=exclusions_by_wrestler.get(
                            wrestler_b, frozenset()
                        ),
                        exclusions_b=exclusions_by_wrestler.get(
                            wrestler_a, frozenset()
                        ),
                        ranking_a=1,
                        ranking_b=2,
                        max_turns=max_turns,
                    )
                )

    return records


def standings(records: list[BoutRecord]) -> list[Standing]:
    wrestlers = sorted(
        {
            name
            for record in records
            for name in (record.wrestler_a, record.wrestler_b)
        }
    )
    rows: list[Standing] = []

    for wrestler in wrestlers:
        relevant = [
            record
            for record in records
            if wrestler in {record.wrestler_a, record.wrestler_b}
        ]
        completed = [record for record in relevant if record.completed]
        wins = sum(record.winner == wrestler for record in completed)
        losses = sum(
            record.winner is not None and record.winner != wrestler
            for record in completed
        )
        rows.append(
            Standing(
                wrestler=wrestler,
                bouts=len(relevant),
                completed_bouts=len(completed),
                wins=wins,
                losses=losses,
                win_rate=(wins / len(completed)) if completed else 0.0,
            )
        )

    return sorted(
        rows,
        key=lambda row: (
            -row.win_rate,
            -row.wins,
            row.wrestler,
        ),
    )


def run_difficulty_series(
    wrestler_a: str,
    wrestler_b: str,
    seed_pairs: Iterable[tuple[int, int]],
    *,
    difficulty_a: int = 0,
    difficulty_b: int = 0,
    ranking_a: int | None = 1,
    ranking_b: int | None = 2,
    max_turns: int = 100,
) -> list[BoutRecord]:
    exclusions_a = exclusions_for_difficulty(
        wrestler_a, difficulty_a
    ).excluded_ids
    exclusions_b = exclusions_for_difficulty(
        wrestler_b, difficulty_b
    ).excluded_ids
    return run_series(
        wrestler_a,
        wrestler_b,
        seed_pairs,
        exclusions_a=exclusions_a,
        exclusions_b=exclusions_b,
        ranking_a=ranking_a,
        ranking_b=ranking_b,
        max_turns=max_turns,
    )


def run_difficulty_round_robin(
    wrestler_names: Iterable[str],
    *,
    difficulty: int = 0,
    bouts_per_orientation: int = 1,
    max_turns: int = 100,
    seed_start: int = 1,
) -> list[BoutRecord]:
    names = list(wrestler_names)
    exclusions = {
        name: exclusions_for_difficulty(name, difficulty).excluded_ids
        for name in names
    }
    return run_round_robin(
        names,
        bouts_per_orientation=bouts_per_orientation,
        exclusions_by_wrestler=exclusions,
        max_turns=max_turns,
        seed_start=seed_start,
    )
