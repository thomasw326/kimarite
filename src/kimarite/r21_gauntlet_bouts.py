"""Runnable, opt-in R21 generic-wrestler bout adapter.

Never invoked by live V5 or its style tests. Uses fixed role-based seeds
and a single balanced seat per fixture; no reverse-seat rematches.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path

from .ai import play_ai_turn
from .catalog import CARD_POOL, STARTING_KIMARITE
from .models import BoutState, Card, FighterState, Side, Wrestler
from .r21_gauntlet import (
    MANIFEST_PATH, Arm, Fixture, ScheduledBout, fixtures, generic_roster,
    load_arms, schedule,
)
from .r21_variant_rules import build_variant_card, variant_predicate
from .tachiai import compare_tachiai, first_exchange_side
from .tachiai_effects import resolve_prepared_tachiai
from .turns import apply_initial_power, end_exchange_turn, start_exchange_turn


@dataclass(frozen=True)
class GauntletResult:
    arm_id: str
    kimarite: str
    placement: str
    fixture_id: str
    seed: int
    subject_index: int
    opponent_index: int
    subject_seat: str
    subject_won: bool
    completed: bool
    finished_by_tested_kimarite: bool
    condition_attained: bool
    tested_card_available: bool
    win_method: str
    turns: int
    error: str


def _role_rng(seed: int, role: str) -> random.Random:
    # Seed by stable role, not A/B. Variants use identical role-based decks.
    digest = hashlib.sha256(f"r21:{seed}:{role}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _build_generic(
    profile_index: int,
    *,
    seed: int,
    role: str,
    arm: Arm | None = None,
    placement: str = "starting",
    variant_id: int = 50001,
    ranking: int,
) -> FighterState:
    profile = generic_roster()[profile_index]
    rng = _role_rng(seed, role)

    # Every family gets an independent, reproducible neutral baseline Kimarite.
    # If the test variant occupies the shuffled slot, this remains at setup.
    available_starters = [
        card for card in STARTING_KIMARITE
        if arm is None or card.name != arm.kimarite
    ]
    baseline = rng.choice(available_starters)
    variant = build_variant_card(arm.arm_id, card_id=variant_id) if arm else None
    if arm is not None and placement == "starting":
        starting = variant
    else:
        starting = baseline

    # No named-wrestler style affinity, exclusions or decks.
    basics = [card for card in CARD_POOL if not card.is_kimarite]
    tachiai = rng.choice(basics)
    top = rng.choice([card for card in basics if card.name != tachiai.name])
    prohibited = {starting.name, tachiai.name, top.name}
    if arm is not None:
        prohibited.add(arm.kimarite)  # prevent legacy same-name duplication

    remainder = [card for card in CARD_POOL if card.name not in prohibited]
    if variant is not None and placement == "shuffled":
        remainder.append(variant)
    rng.shuffle(remainder)

    wrestler = Wrestler(
        profile.name, *profile.stats, starting, tachiai, top,
        primary=profile.priorities[0],
        secondary=profile.priorities[1],
        tertiary=profile.priorities[2],
        ranking=ranking,
    )
    return FighterState(
        wrestler,
        draw_pile=[top, *remainder, tachiai],
        kimarite_zone=[starting],
    )


def prepare_fixture(arm: Arm, bout: ScheduledBout) -> tuple[BoutState, Card, Side]:
    """Prepare one fixture without mutating live card definitions."""
    if bout.arm_id != arm.arm_id or bout.placement not in ("starting", "shuffled"):
        raise ValueError("Fixture does not match R21 experimental arm/placement")
    arm_order = {a.arm_id: i for i, a in enumerate(load_arms(), start=1)}
    experimental = build_variant_card(arm.arm_id, card_id=50000 + arm_order[arm.arm_id])
    subject = _build_generic(
        bout.subject_index, seed=bout.seed, role="subject",
        arm=arm, placement=bout.placement,
        variant_id=experimental.card_id,
        ranking=bout.subject_index + 1,
    )
    opponent = _build_generic(
        bout.opponent_index, seed=bout.seed, role="opponent",
        arm=None, ranking=bout.opponent_index + 1,
    )
    if bout.subject_seat == "A":
        state, side = BoutState(subject, opponent, r21_active=True), Side.A
    elif bout.subject_seat == "B":
        state, side = BoutState(opponent, subject, r21_active=True), Side.B
    else:
        raise ValueError("Unknown seat")
    if arm.arm_id == "R21-HIK-RS" and bout.placement == "starting":
        from .r21_search import search_for_reversal
        search_for_reversal(state.fighter(side))
    return state, experimental, side


def _available(state: BoutState, side: Side, experimental: Card) -> bool:
    f = state.fighter(side)
    return (
        experimental in f.kimarite_zone
        or experimental in f.hand
        or any(card_id == experimental.card_id and owner is side
               for owner, card_id in state.card_play_ids)
    )


def run_fixture(arm: Arm, bout: ScheduledBout, *, max_turns: int = 30) -> GauntletResult:
    state, experimental, subject_side = prepare_fixture(arm, bout)
    cmp = compare_tachiai(state.fighter_a.wrestler, state.fighter_b.wrestler)
    apply_initial_power(state, cmp)
    # Neutral control: decline Headlong sacrifice on both generic fighters.
    choices = {}
    seen_condition = False
    seen_available = _available(state, subject_side, experimental)
    error = ""
    try:
        resolve_prepared_tachiai(state, cmp, sacrifice_choices=choices)
        if state.winner is None:
            state.active_side = first_exchange_side(
                cmp, state.fighter_a.wrestler, state.fighter_b.wrestler
            )
        for _ in range(max_turns):
            if state.winner is not None:
                break
            side = state.active_side
            if side is None:
                raise RuntimeError("Missing active side")
            start_exchange_turn(state, side, cmp)
            seen_condition |= variant_predicate(state, subject_side, arm.arm_id)
            seen_available |= _available(state, subject_side, experimental)
            if state.winner is not None:
                break
            play_ai_turn(state, side, cmp)
            seen_condition |= variant_predicate(state, subject_side, arm.arm_id)
            seen_available |= _available(state, subject_side, experimental)
            if state.winner is not None:
                break
            end_exchange_turn(state, side)
            seen_condition |= variant_predicate(state, subject_side, arm.arm_id)
            seen_available |= _available(state, subject_side, experimental)
        if state.winner is None:
            error = f"Turn limit {max_turns}"
    except (KeyError, ValueError, RuntimeError, NotImplementedError) as exc:
        error = f"{type(exc).__name__}: {exc}"

    completed = state.winner is not None
    win = completed and state.winner is subject_side
    return GauntletResult(
        arm_id=arm.arm_id, kimarite=arm.kimarite, placement=bout.placement,
        fixture_id=bout.fixture_id, seed=bout.seed,
        subject_index=bout.subject_index, opponent_index=bout.opponent_index,
        subject_seat=bout.subject_seat, subject_won=win, completed=completed,
        finished_by_tested_kimarite=bool(
            win and state.win_source == "kimarite"
            and state.winning_kimarite_card_id == experimental.card_id
        ),
        condition_attained=seen_condition,
        tested_card_available=seen_available,
        win_method=state.win_method or "",
        turns=state.turn_number,
        error=error,
    )


def execute_batch(
    *, arm_ids: tuple[str, ...], seed: int, start: int, count: int,
    max_turns: int, output: Path
) -> dict[str, object]:
    if start < 0 or count < 1 or max_turns < 1:
        raise ValueError("start >= 0, count >= 1 and max_turns >= 1 required")
    arms = load_arms()
    by_id = {arm.arm_id: arm for arm in arms}
    if any(arm_id not in by_id for arm_id in arm_ids):
        raise ValueError("Unknown experimental arm")
    selected = tuple(by_id[arm_id] for arm_id in arm_ids) if arm_ids else arms
    output.parent.mkdir(parents=True, exist_ok=True)
    n, wins, finishes, failures = 0, 0, 0, 0
    with output.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(GauntletResult.__dataclass_fields__))
        writer.writeheader()
        # Iteration is deterministic; no full 90,720-row schedule in memory.
        for i, bout in enumerate(schedule(selected, seed=seed)):
            if i < start:
                continue
            if i >= start + count:
                break
            result = run_fixture(by_id[bout.arm_id], bout, max_turns=max_turns)
            writer.writerow(vars(result))
            n += 1
            wins += int(result.subject_won)
            finishes += int(result.finished_by_tested_kimarite)
            failures += int(not result.completed or bool(result.error))
    if not n:
        raise ValueError("Selected offset starts beyond scheduled fixtures")
    return {
        "status": "completed experiment batch",
        "output": str(output),
        "seed": seed, "start": start, "count": n,
        "arms": [a.arm_id for a in selected], "wins": wins,
        "experimental_kimarite_finishes": finishes,
        "incomplete_or_error": failures,
        "seat_note": "A/B orientation is a symmetry diagnostic, not a primary balance input.",
        "design_source_sha256": hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", action="append", default=[], dest="arms",
                        help="Arm ID to run; omit for all 70")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--count", type=int, default=100,
                        help="Safety-bounded number of bouts in this local batch")
    parser.add_argument("--max-turns", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20261010)
    parser.add_argument("--output", type=Path, default=Path("artifacts/r21_batch.csv"))
    args = parser.parse_args()
    print(json.dumps(execute_batch(
        arm_ids=tuple(args.arms), seed=args.seed, start=args.start,
        count=args.count, max_turns=args.max_turns, output=args.output
    ), indent=2))


if __name__ == "__main__":
    main()
