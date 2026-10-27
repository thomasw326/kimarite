"""Construct a B11 human/AI bout after the irreversible opening commitment.

Classic _fighter and session setup are not modified. This function is an
engine-only handoff; the browser API stays preview-only until a complete,
transactional start-turn and public-state integration is verified.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass

from .b10_human_session import ROSTER_PATH, STYLE_PROXIES, _fighter
from .b11_pending_session import PendingB11Session
from .b11_player_tachiai import compare_player_tachiai
from .catalog import card_by_name
from .models import BoutState, FighterState, Side, Stat, Wrestler
from .styles_v5 import STYLES
from .tachiai import first_exchange_side
from .tachiai_effects import resolve_prepared_tachiai
from .turns import apply_initial_power


@dataclass
class ResolvedB11Opening:
    state: BoutState
    comparison: object


def build_resolved_b11_opening(pending: PendingB11Session, *, seed: int = 20261021) -> ResolvedB11Opening:
    """Resolve a chosen human opening, retaining its uncommitted cards in hand."""
    if pending.phase.pending:
        raise ValueError("Commit the opening before resolution.")
    prepared = pending.prepare_resolution()
    # Reveal planning is useful for validation, but the live resolver must
    # consume its own reveal chain exactly once from the unallocated deck.
    full_deck = [card_by_name(n) for n in json.loads(ROSTER_PATH.read_text(encoding="utf-8"))["decks"][pending.human]["cards"]]
    unallocated = pending.phase.decision.unallocated_deck(pending.phase.opening, full_deck)
    # Match Classic's seeded shuffle after physical opening cards are removed.
    # Without this, the roster JSON order groups Kimarite near the draw top.
    random.Random(seed * 2).shuffle(unallocated)
    records = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))["decks"]
    human_record = records[pending.human]
    ai = _fighter(pending.opponent, records[pending.opponent], seed=seed * 2 + 1, ranking=2)
    style = STYLES[STYLE_PROXIES.get(pending.human, pending.human)]
    order = list(dict.fromkeys([style.primary, style.secondary]))
    order.extend(x.value for x in (Stat.POWER, Stat.TECHNIQUE, Stat.SPIRIT) if x.value not in order)
    # B11 human has three base points: primary 2, secondary 1, tertiary 0.
    # AI retains its six-point roster stats to offset its two-card Tachiai.
    stats = dict.fromkeys((Stat.POWER.value, Stat.TECHNIQUE.value, Stat.SPIRIT.value), 0)
    stats[order[0]] = 2
    stats[order[1]] = 1
    blank = card_by_name("Oshi")  # unused classic-role placeholders; never zoned
    human = Wrestler(
        pending.human, stats["power"], stats["technique"], stats["spirit"],
        blank, blank, blank,
        primary=Stat(order[0]), secondary=Stat(order[1]), tertiary=Stat(order[2]),
        ranking=1,
    )
    own = FighterState(
        human, draw_pile=unallocated,
        hand=list(prepared.retained_hand),
        discard_pile=[],
    )
    state = BoutState(own, ai)
    state.b11_explain_wins = True
    comparison = compare_player_tachiai(human, ai.wrestler, prepared.committed)
    # Each committed reveal chain is consumed by the live resolver once.
    apply_initial_power(state, comparison)
    resolve_prepared_tachiai(
        state, comparison, committed_cards={Side.A: prepared.committed},
    )
    if state.winner is None:
        state.active_side = first_exchange_side(comparison, human, ai.wrestler)
    return ResolvedB11Opening(state, comparison)


def start_b11_human_bout(pending: PendingB11Session, *, max_turns: int = 100):
    """Turn a committed opening into the existing interactive HumanBout."""
    from .human_bout import HumanBout
    from .style_ai_v5 import play_style_turn
    result = build_resolved_b11_opening(pending, seed=pending.seed)
    def opponent_turn(state, side, comparison):
        return play_style_turn(
            state, side, comparison,
            STYLE_PROXIES.get(pending.opponent, pending.opponent),
        )
    session = HumanBout(result.state, result.comparison, Side.A, opponent_turn, max_turns)
    # B11 public serialization must never invent Classic prepared/top slots.
    session.b11_opening = {
        "allocated": pending.phase.decision.allocated,
        "committed": pending.phase.decision.committed,
        "retained": pending.phase.decision.retained,
    }
    session.annotate_turns = True
    session.advance()
    return session
