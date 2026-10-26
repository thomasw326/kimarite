"""Construct a B11 human/AI bout after the irreversible opening commitment.

Classic _fighter and session setup are not modified. This function is an
engine-only handoff; the browser API stays preview-only until a complete,
transactional start-turn and public-state integration is verified.
"""
from __future__ import annotations

import json
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
    records = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))["decks"]
    human_record = records[pending.human]
    ai = _fighter(pending.opponent, records[pending.opponent], seed=seed * 2 + 1, ranking=2)
    style = STYLES[STYLE_PROXIES.get(pending.human, pending.human)]
    order = list(dict.fromkeys([style.primary, style.secondary]))
    order.extend(x.value for x in (Stat.POWER, Stat.TECHNIQUE, Stat.SPIRIT) if x.value not in order)
    stats = human_record["stats"]
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
    comparison = compare_player_tachiai(human, ai.wrestler, prepared.committed)
    # Each committed reveal chain is consumed by the live resolver once.
    apply_initial_power(state, comparison)
    resolve_prepared_tachiai(
        state, comparison, committed_cards={Side.A: prepared.committed},
    )
    if state.winner is None:
        state.active_side = first_exchange_side(comparison, human, ai.wrestler)
    return ResolvedB11Opening(state, comparison)
