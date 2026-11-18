"""Construct a live B11 bout after the opening decisions are locked."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, replace

from .b10_human_session import ROSTER_PATH, STYLE_PROXIES, _fighter
from .b11_pending_session import PendingB11Session
from .b11_player_tachiai import compare_player_tachiai
from .catalog import card_by_name
from .models import BoutState, Card, FighterState, Side, Stat, Wrestler
from .styles_v5 import STYLES
from .tachiai import first_exchange_side
from .tachiai_effects import resolve_prepared_tachiai
from .turns import apply_initial_power


@dataclass
class ResolvedB11Opening:
    state: BoutState
    comparison: object


def build_b12_opponent(pending: PendingB11Session, seed: int) -> FighterState:
    from .b12_ai_day import build_ai_fighter
    from .b12_division_roster import load_formats

    opponent = pending.opponent_ai
    framework = next(f for f in load_formats() if f["id"] == opponent["format_id"])
    return build_ai_fighter(opponent, framework, seed * 2 + 1, opponent["wins"])


def rematch_tachiai_cards(ai: FighterState) -> tuple[Card, Card, Card]:
    wrestler = ai.wrestler
    return (wrestler.starting_kimarite, wrestler.prepared_tachiai_card,
            wrestler.top_of_deck_card)


def build_resolved_b11_opening(
    pending: PendingB11Session, *, seed: int = 20261021, rematch_index: int | None = None,
) -> ResolvedB11Opening:
    """Resolve a chosen human opening, retaining its uncommitted cards in hand."""
    if pending.phase.pending:
        raise ValueError("Commit the opening before resolution.")
    prepared = pending.prepare_resolution()
    # Reveal planning is useful for validation, but the live resolver must
    # consume its own reveal chain exactly once from the unallocated deck.
    full_deck = [card_by_name(n) for n in (pending.drafted_deck if pending.drafted_deck is not None else json.loads(ROSTER_PATH.read_text(encoding="utf-8"))["decks"][pending.human]["cards"])]
    unallocated = pending.phase.decision.unallocated_deck(pending.phase.opening, full_deck)
    # Match Classic's seeded shuffle after physical opening cards are removed.
    # Without this, the roster JSON order groups Kimarite near the draw top.
    random.Random(seed * 2).shuffle(unallocated)
    records = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))["decks"]
    if pending.opponent_ai is None:
        ai = _fighter(pending.opponent, records[pending.opponent], seed=seed * 2 + 1, ranking=2)
    else:
        ai = build_b12_opponent(pending, seed)
    if rematch_index is not None:
        selected = rematch_tachiai_cards(ai)[rematch_index]
        if selected is not ai.draw_pile[0]:
            # Keep the original Kimarite and prepared effect in their normal
            # zones. The extra physical copy lives only in this bout.
            selected = replace(selected)
            ai.draw_pile.insert(0, selected)
            ai.wrestler = replace(ai.wrestler, top_of_deck_card=selected)
    # Player-created wrestlers use their chosen 2/1/0 allocation, without
    # consulting any roster style or prescribing a fighter archetype.
    if pending.created_stats is not None:
        stats = dict(pending.created_stats)
        order = [key.capitalize() for key in sorted(stats, key=lambda key: (-stats[key], key))]
    else:
        # Retain historical B11 preset-wrestler behavior for practice tests.
        style = STYLES[STYLE_PROXIES.get(pending.human, pending.human)]
        order = list(dict.fromkeys([style.primary, style.secondary]))
        order.extend(x.value for x in (Stat.POWER, Stat.TECHNIQUE, Stat.SPIRIT) if x.value not in order)
        stats = {"power": 0, "technique": 0, "spirit": 0}
        stats[order[0].lower()] = 2
        stats[order[1].lower()] = 1
    # The AI retains its existing six-point roster stats and hidden Tachiai.
    blank = card_by_name("Oshi")  # unused classic-role placeholders; never zoned
    human = Wrestler(
        pending.human, stats["power"], stats["technique"], stats["spirit"],
        blank, blank, blank,
        primary=Stat(order[0]), secondary=Stat(order[1]), tertiary=Stat(order[2]),
        ranking=pending.player_rank,
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


def start_b11_human_bout(
    pending: PendingB11Session, *, max_turns: int = 100, rematch_index: int | None = None,
):
    """Turn a committed opening into the existing interactive HumanBout."""
    from .human_bout import HumanBout
    from .style_ai_v5 import play_style_turn
    result = build_resolved_b11_opening(pending, seed=pending.seed, rematch_index=rematch_index)
    def opponent_turn(state, side, comparison):
        return play_style_turn(
            state, side, comparison,
            pending.opponent_ai["style"] if pending.opponent_ai is not None
            else STYLE_PROXIES.get(pending.opponent, pending.opponent),
        )
    session = HumanBout(result.state, result.comparison, Side.A, opponent_turn, max_turns)
    # B11 public serialization must never invent Classic prepared/top slots.
    session.b11_opening = {
        "allocated": pending.phase.decision.allocated,
        "committed": pending.phase.decision.committed,
        "retained": pending.phase.decision.retained,
    }
    if rematch_index is not None:
        session.rematch_index = rematch_index
        session.tachiai_commitment = pending.phase.decision.indices
    session.annotate_turns = True
    session.advance()
    return session
