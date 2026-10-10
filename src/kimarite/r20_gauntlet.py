"""Deterministic generic-wrestler schedule for the R20 Kimarite gauntlet.

Design boundary: this module does NOT claim the live V5 engine implements R20
variants. The catalogue is kept separate from the existing card IDs and style
assignments until variant-aware win/effect dispatch is verified.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from itertools import permutations
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from .models import Stat


MANIFEST_PATH = Path(__file__).resolve().parents[2] / "data" / "r20_kimarite_arms.json"
STAT_BUILDS: tuple[tuple[int, int, int], ...] = (
    (4, 1, 0), (4, 0, 1), (3, 2, 0), (3, 0, 2),
    (3, 1, 1), (2, 2, 1), (2, 1, 2), (1, 4, 0),
    (0, 4, 1), (2, 3, 0), (0, 3, 2), (1, 3, 1),
    (1, 2, 2), (1, 0, 4), (0, 1, 4), (2, 0, 3),
    (0, 2, 3), (1, 1, 3),
)
PLACEMENTS = ("starting", "shuffled")
# Rotations on the generic roster. Every configuration encounters six distinct
# other configurations and is the opponent in six, avoiding per-card assignment
# and any one wrestler's thematic card affinity.
DEFAULT_OPPONENT_OFFSETS = (1, 11, 23, 37, 53, 79)


@dataclass(frozen=True)
class Profile:
    index: int
    stats: tuple[int, int, int]
    priorities: tuple[Stat, Stat, Stat]

    @property
    def name(self) -> str:
        return f"G{self.index:03d}"


@dataclass(frozen=True)
class Arm:
    arm_id: str
    kimarite: str
    orbs: str
    source_row: int
    win_text: str
    exchange_text: str


@dataclass(frozen=True)
class Fixture:
    """One paired setup, independent of R20 variant or seat orientation."""

    fixture_id: str
    subject_index: int
    opponent_index: int
    seed: int


@dataclass(frozen=True)
class ScheduledBout:
    arm_id: str
    kimarite: str
    placement: str
    fixture_id: str
    subject_index: int
    opponent_index: int
    subject_seat: str
    seed: int


@dataclass(frozen=True)
class BoutRecord:
    """Outcome contract to be emitted by the future variant-aware engine.

    Condition attainment means the card's win predicate was observed true,
    whether or not it ultimately won. Availability means the tested Kimarite
    was accessible in the Kimarite Zone or hand during that bout.
    """

    arm_id: str
    placement: str
    subject_seat: str
    completed: bool
    subject_won: bool = False
    finished_by_tested_kimarite: bool = False
    condition_attained: bool = False
    tested_card_available: bool = False
    error: str = ""


@lru_cache(maxsize=4)
def load_arms(path: Path = MANIFEST_PATH) -> tuple[Arm, ...]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported R20 manifest schema version")
    arms = tuple(
        Arm(
            arm_id=record["id"],
            kimarite=record["Kimarite"],
            orbs=record["Printed orbs"],
            source_row=int(record["source_row"]),
            win_text=record["Condition summary"],
            exchange_text=record["Exchange result"],
        )
        for record in data["arms"]
    )
    if not arms or len(set(a.arm_id for a in arms)) != len(arms):
        raise ValueError("Missing or duplicate R20 variant IDs")
    if any(a.orbs in ("", "TBD") or not a.exchange_text for a in arms):
        raise ValueError("R20 variant missing orbs or an Exchange effect")
    return arms


@lru_cache(maxsize=4)
def generic_roster() -> tuple[Profile, ...]:
    return tuple(
        Profile(index, stats, order)
        for index, (stats, order) in enumerate(
            (pair for stats in STAT_BUILDS for pair in
             ((stats, order) for order in permutations(Stat))), 1
        )
    )


def fixtures(
    *, seed: int = 20261010,
    opponent_offsets: tuple[int, ...] = DEFAULT_OPPONENT_OFFSETS,
) -> tuple[Fixture, ...]:
    roster = generic_roster()
    n = len(roster)
    if not opponent_offsets or len(set(opponent_offsets)) != len(opponent_offsets):
        raise ValueError("Opponent offsets must be distinct and nonempty")
    if any(offset <= 0 or offset >= n for offset in opponent_offsets):
        raise ValueError("Opponent offsets must be within 1..roster size - 1")
    return tuple(
        Fixture(
            fixture_id=f"{i:03d}-{j:02d}",
            subject_index=i,
            opponent_index=(i + offset) % n,
            seed=seed + i * 100 + j,
        )
        for i in range(n)
        for j, offset in enumerate(opponent_offsets)
    )


def schedule(
    arms: Iterable[Arm],
    *,
    seed: int = 20261010,
    opponent_offsets: tuple[int, ...] = DEFAULT_OPPONENT_OFFSETS,
) -> Iterable[ScheduledBout]:
    """Return mirror-paired fixtures; only a diagnostic role for seat order.

    The game is almost fully symmetric. Rotating A/B detects unexpected
    first-mover/tie resolution effects, but seat position is NOT our primary
    explanatory variable. Seeds, opponent fixtures, and subject stat builds are
    held fixed across the arms of each Kimarite.
    """
    fixed = fixtures(seed=seed, opponent_offsets=opponent_offsets)
    for arm in arms:
        for placement in PLACEMENTS:
            for fixture in fixed:
                for subject_seat in ("A", "B"):
                    yield ScheduledBout(
                        arm_id=arm.arm_id,
                        kimarite=arm.kimarite,
                        placement=placement,
                        fixture_id=fixture.fixture_id,
                        subject_index=fixture.subject_index,
                        opponent_index=fixture.opponent_index,
                        subject_seat=subject_seat,
                        seed=fixture.seed,
                    )


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def summarize_records(records: Iterable[BoutRecord]) -> list[dict[str, object]]:
    """Descriptive metrics, no aggregate 'best arm' score or balance verdict.

    All denominators and missing/incomplete outcomes stay visible. Seat data is
    recorded as an audit diagnostic, not interpreted as a balance ranking.
    """
    by_group: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    for record in records:
        if record.placement not in PLACEMENTS or record.subject_seat not in ("A", "B"):
            raise ValueError("Unknown placement or seat in bout record")
        if record.finished_by_tested_kimarite and (
            not record.completed or not record.subject_won
        ):
            raise ValueError("A tested Kimarite finish must be a completed win")
        if record.subject_won and not record.completed:
            raise ValueError("An incomplete bout cannot be a win")
        c = by_group[(record.arm_id, record.placement)]
        c["scheduled"] += 1
        c[f"seat_{record.subject_seat}"] += 1
        c["completed"] += int(record.completed)
        c["incomplete"] += int(not record.completed)
        c["errors"] += int(bool(record.error))
        c["wins"] += int(record.subject_won)
        c["finishes"] += int(record.finished_by_tested_kimarite)
        if record.completed:
            c["condition_attainments"] += int(record.condition_attained)
            c["available"] += int(record.tested_card_available)
            if record.tested_card_available and record.finished_by_tested_kimarite:
                c["finishes_when_available"] += 1
    output: list[dict[str, object]] = []
    for (arm_id, placement), c in sorted(by_group.items()):
        completed = c["completed"]
        output.append({
            "arm_id": arm_id,
            "placement": placement,
            "scheduled": c["scheduled"],
            "completed": completed,
            "incomplete": c["incomplete"],
            "errors": c["errors"],
            "wins": c["wins"],
            "kimarite_finishes": c["finishes"],
            "condition_attainments": c["condition_attainments"],
            "tested_card_available": c["available"],
            "seat_A": c["seat_A"],
            "seat_B": c["seat_B"],
            "win_rate": _ratio(c["wins"], completed),
            "kimarite_completion_rate": _ratio(c["finishes"], completed),
            "condition_attainment_rate": _ratio(c["condition_attainments"], completed),
            "availability_rate": _ratio(c["available"], completed),
            "completion_given_availability": _ratio(
                c["finishes_when_available"], c["available"]
            ),
        })
    return output


def plan_summary(arms: tuple[Arm, ...], samples_per_build: int) -> dict[str, object]:
    roster_count = len(generic_roster())
    per_arm_per_placement = roster_count * samples_per_build * 2
    return {
        "experiment": "R20 generic Kimarite gauntlet",
        "mode": "schedule-only; variant-aware R20 combat implementation pending",
        "number_of_variants": len(arms),
        "number_of_kimarite": len({a.kimarite for a in arms}),
        "generic_stat_priority_profiles": roster_count,
        "opponent_samples_per_profile": samples_per_build,
        "seat_orientations": 2,
        "placements": list(PLACEMENTS),
        "bouts_per_arm_per_placement": per_arm_per_placement,
        "planned_bouts": len(arms) * len(PLACEMENTS) * per_arm_per_placement,
        "seat_policy": (
            "Seat A/B is a mirrored symmetry diagnostic; only uncommon opening "
            "ties or first-mover tie-breaks are expected to matter."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20261010)
    parser.add_argument("--plan-csv", type=Path,
                        help="Write every scheduled bout to CSV; no bouts are run")
    parser.add_argument("--run", action="store_true",
                        help="Reserved until R20 variant-aware engine is verified")
    args = parser.parse_args()
    if args.run:
        parser.error(
            "R20 win predicates/Exchange effects are not yet implemented for "
            "every arm. Refusing misleading simulation results."
        )
    arms = load_arms()
    plan = plan_summary(arms, len(DEFAULT_OPPONENT_OFFSETS))
    if args.plan_csv:
        args.plan_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.plan_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow((
                "arm_id", "kimarite", "placement", "fixture_id", "subject_index",
                "opponent_index", "subject_seat", "seed"
            ))
            for bout in schedule(arms, seed=args.seed):
                writer.writerow((
                    bout.arm_id, bout.kimarite, bout.placement, bout.fixture_id,
                    bout.subject_index, bout.opponent_index,
                    bout.subject_seat, bout.seed
                ))
        plan["plan_csv"] = str(args.plan_csv)
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
