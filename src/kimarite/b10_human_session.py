"""UI-ready B10 human-versus-State-3-AI session, independent of terminal IO.

The public snapshot intentionally exposes only human-visible information.
No card rules, AI scoring or deck data are modified here.
"""
from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import random

from .catalog import card_by_name
from .b10_card_info import card_info, GLOSSARY

from .human_bout import HumanBout
from .models import BoutState, FighterState, Side, Stat, Wrestler, GripState
from .rules import grip_benefits_suppressed
from .style_ai_v5 import play_style_turn
from .styles_v5 import STYLES
from .tachiai import compare_tachiai, first_exchange_side
from .tachiai_effects import resolve_prepared_tachiai
from .turns import apply_initial_power

VERIFIED_CARD_TEXT = {
    "Katasukashi": "Win condition: Opponent has no Grip; your relative Momentum is +2 or higher; you have at least 4 more cards in hand than your opponent.",
    "Pull": "Exchange: Lose 1 Position. Gain 1 Momentum. Make the opponent Unstable. Draw 1 card, then discard 1 card from your hand.",
    "Give Ground": "Exchange: Lose 1 Position. Gain 1 Momentum and 1 Power. Draw 1 card.",
}
def rules_text(name: str) -> str:
    return VERIFIED_CARD_TEXT.get(name, "Detailed B10 rules text not yet verified — inspect card name and orbs only.")

ROSTER_PATH = Path(__file__).resolve().parents[2] / "data" / "b9_30_wrestler_decks.json"
EXCLUDED = frozenset({"Attrition Fighter", "Disruptor", "Gripless Fighter", "Stability Master"})
# Exactly the proxy style assignments used in the approved tournament runner.
STYLE_PROXIES = {
    "Dancer": "The Specialist", "Momentum Twister": "The Technician",
    "Attrition Fighter": "Disruptor", "Gripless Fighter": "Opportunist",
    "Hand-Size Specialist": "The Specialist", "Inside Fighter": "Mawashi Specialist",
    "Outside Fighter": "The Technician", "Double-Grip Wrestler": "Power Grappler",
    "Lifting Specialist": "Power Grappler", "Stability Master": "Unorthodox Powerhouse",
    "Arm Controller": "Disruptor", "Pull-Down Specialist": "Opportunist",
    "Counter Wrestler": "The Specialist", "Ring-Edge Defender": "Mountain",
    "Power Finisher": "Heavy Hitter",
}


def management_deal(name: str, seed: int) -> dict:
    """Deal 3 Kimarite and 6 ordinary cards, using actual approved deck copies."""
    if name not in roster():
        raise ValueError("Unknown wrestler")
    data = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))["decks"][name]["cards"]
    rng = random.Random(seed)
    kimarite = [card_by_name(n) for n in data if card_by_name(n).is_kimarite]
    ordinary = [card_by_name(n) for n in data if not card_by_name(n).is_kimarite]
    if len(kimarite) < 3 or len(ordinary) < 6:
        raise ValueError("Deck cannot supply three playable openings")
    chosen = rng.sample(kimarite, 3) + rng.sample(ordinary, 6)
    rng.shuffle(chosen)
    return {"wrestler": name, "seed": seed,
            "cards": [{**card_info(card), "deal_index": i} for i, card in enumerate(chosen)]}


def opening_options(name: str) -> dict:
    if name not in roster():
        raise ValueError("Unknown wrestler")
    cards = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))["decks"][name]["cards"]
    return {
        "kimarite": [card_info(card_by_name(n)) for n in dict.fromkeys(cards) if card_by_name(n).is_kimarite],
        "ordinary": [card_info(card_by_name(n)) for n in dict.fromkeys(cards) if not card_by_name(n).is_kimarite],
    }


def roster() -> tuple[str, ...]:
    records = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))["decks"]
    names = tuple(n for n in records if n not in EXCLUDED)
    if len(names) != 26:
        raise ValueError("The B10 human play roster must contain exactly 26 wrestlers")
    return names


def _fighter(name: str, record: dict, *, seed: int, ranking: int, opening: dict | None = None) -> FighterState:
    rng = random.Random(seed)
    cards = [card_by_name(n) for n in record["cards"]]
    kimarite = [c for c in cards if c.is_kimarite]
    ordinary = [c for c in cards if not c.is_kimarite]
    if len(cards) != 40 or not kimarite or len(ordinary) < 2:
        raise ValueError(f"Invalid B10 deck for {name}")
    if opening is None:
        starting_kimarite = kimarite.pop(rng.randrange(len(kimarite)))
        prepared = ordinary.pop(rng.randrange(len(ordinary)))
        top = ordinary.pop(rng.randrange(len(ordinary)))
    else:
        from collections import Counter
        keys = ("kimarite", "prepared", "top")
        if any(key not in opening or not isinstance(opening[key], str) for key in keys):
            raise ValueError("Choose three valid opening cards")
        requested = [opening[key] for key in keys]
        counts = Counter(record["cards"])
        if any(n > counts[name] for name, n in Counter(requested).items()):
            raise ValueError("Selected opening cards exceed available copies")
        def take(pool, name):
            for i, card in enumerate(pool):
                if card.name == name:
                    return pool.pop(i)
            raise ValueError("Opening card has the wrong role")
        starting_kimarite = take(kimarite, requested[0])
        prepared = take(ordinary, requested[1])
        top = take(ordinary, requested[2])
    remaining = kimarite + ordinary
    rng.shuffle(remaining)
    model = STYLES[STYLE_PROXIES.get(name, name)]
    order = list(dict.fromkeys([model.primary, model.secondary]))
    order.extend(x.value for x in (Stat.POWER, Stat.TECHNIQUE, Stat.SPIRIT) if x.value not in order)
    stats = record["stats"]
    wrestler = Wrestler(
        name, stats["power"], stats["technique"], stats["spirit"],
        starting_kimarite, prepared, top,
        primary=Stat(order[0]), secondary=Stat(order[1]), tertiary=Stat(order[2]),
        ranking=ranking,
    )
    return FighterState(wrestler, draw_pile=[top, *remaining], kimarite_zone=[starting_kimarite])


def new_b10_session(human: str, opponent: str, *, seed: int = 20261021,
                    max_turns: int = 100, opening: dict | None = None) -> HumanBout:
    """Build the same 40-card wrestler fixtures and neutral State-3 AI as B10 testing."""
    if human not in roster() or opponent not in roster():
        raise ValueError("Both wrestlers must belong to the approved 26-wrestler roster")
    if max_turns < 1:
        raise ValueError("max_turns must be positive")
    records = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))["decks"]
    a = _fighter(human, records[human], seed=seed * 2, ranking=1, opening=opening)
    b = _fighter(opponent, records[opponent], seed=seed * 2 + 1, ranking=2)
    state = BoutState(a, b)
    comparison = compare_tachiai(a.wrestler, b.wrestler)
    apply_initial_power(state, comparison)
    resolve_prepared_tachiai(state, comparison)
    if state.winner is None:
        state.active_side = first_exchange_side(comparison, a.wrestler, b.wrestler)
    def opponent_turn(state, side, comparison):
        return play_style_turn(state, side, comparison, STYLE_PROXIES.get(opponent, opponent))
    # Opening setup is public to the player: cards and base/printed-orb totals.
    # Preserve the frozen tournament's randomized starting selections.
    opening_events = [
        f"Tachiai setup — {human}: base Power {a.wrestler.base_power}, Technique {a.wrestler.base_technique}, Spirit {a.wrestler.base_spirit}.",
        f"Tachiai setup — {human}: starting Kimarite {a.wrestler.starting_kimarite.name}, prepared {a.wrestler.prepared_tachiai_card.name}, top deck card {a.wrestler.top_of_deck_card.name}.",
        f"Tachiai orbs — {human}: Power {comparison.wrestler_a.power}, Technique {comparison.wrestler_a.technique}, Spirit {comparison.wrestler_a.spirit}.",
        f"Tachiai orbs — {opponent}: Power {comparison.wrestler_b.power}, Technique {comparison.wrestler_b.technique}, Spirit {comparison.wrestler_b.spirit}.",
        f"Opening Position {state.position:+d}, Momentum {state.momentum:+d} from {human}'s perspective after Tachiai.",
    ]
    state.event_log[:0] = opening_events
    session = HumanBout(state, comparison, Side.A, opponent_turn, max_turns)
    session.advance()
    return session


def public_snapshot(session: HumanBout) -> dict:
    """JSON-compatible display state; never expose opposing hidden cards."""
    view = session.view()
    own = session.state.fighter(session.human_side)
    other = session.state.opponent(session.human_side)
    def shown_card(card):
        return card_info(card)
    def enriched(card):
        result = asdict(card)
        return card_info(card)
    legal_indices = {x.hand_index for x in session.actions()}
    def reason(index, card):
        if index in legal_indices:
            return None
        if session.finished:
            return "The bout has ended."
        if session.pending_selection:
            return "Finish selecting your cards first."
        if not session.awaiting_human:
            return "Wait for your turn."
        if own.plays_remaining <= 0:
            return "No Plays remaining. End your turn."
        if grip_benefits_suppressed(session.state, session.human_side) and card.name in {
            "Gain Left Grip", "Gain Right Grip", "Uwate", "Shitate",
            "Attempt Two-Handed Grip", "Attempt Deep Outside Grip",
            "Attempt Deep Inside Grip", "Morozashi",
        }:
            return "Your Grip effects are suppressed (Kannuki)."
        if card.name == "Morozashi" and own.left_grip is GripState.NONE and own.right_grip is GripState.NONE:
            return "Morozashi requires at least one existing Grip."
        if card.name in {"Okuridashi", "Okuritaoshi"}:
            return "This generated Kimarite cannot be played from hand."
        if card.name == "Headlong Charge" and not own.kimarite_zone:
            return "Headlong Charge requires a Kimarite in your zone."
        if card.name in {"Sidestep", "Spin Away"} and session.state.side_by_side_owner is not None:
            return "Cannot play while already side-by-side."
        return "This card is currently unavailable."
    def recorded_play(side, name):
        return {"player":"You" if side == session.human_side else "Opponent", "card":name}
    opening_override = getattr(session, "b11_opening", None)
    if opening_override is not None:
        human_opening = {
            "mode": "player_controlled",
            "allocated": [card_info(c) for c in opening_override["allocated"]],
            "committed": [card_info(c) for c in opening_override["committed"]],
            "retained": [card_info(c) for c in opening_override["retained"]],
            "base_stats": [own.wrestler.base_power, own.wrestler.base_technique, own.wrestler.base_spirit],
            "tachiai_orbs": [session.comparison.wrestler_a.power, session.comparison.wrestler_a.technique, session.comparison.wrestler_a.spirit],
        }
    else:
        human_opening = {"starting_kimarite":card_info(own.wrestler.starting_kimarite), "prepared_tachiai":card_info(own.wrestler.prepared_tachiai_card), "top_of_deck":card_info(own.wrestler.top_of_deck_card), "base_stats":[own.wrestler.base_power,own.wrestler.base_technique,own.wrestler.base_spirit], "tachiai_orbs":[session.comparison.wrestler_a.power,session.comparison.wrestler_a.technique,session.comparison.wrestler_a.spirit]}
    return {
        "glossary": GLOSSARY,
        "opening": {"human": human_opening, "opponent": {"starting_kimarite":card_info(other.wrestler.starting_kimarite), "prepared_tachiai":card_info(other.wrestler.prepared_tachiai_card), "tachiai_orbs":[session.comparison.wrestler_b.power,session.comparison.wrestler_b.technique,session.comparison.wrestler_b.spirit]}},
        "recent_plays":[recorded_play(side,name) for side,name in session.state.card_plays[-30:]],
        "events":session.state.event_log[:],
        "phase": "finished" if session.finished else
                 "select_cards" if session.pending_selection else
                 "human_turn" if session.awaiting_human else "ai_turn",
        "finished": session.finished,
        "stopped_reason": session.stopped_reason,
        "winner": view.winner.value if view.winner is not None else None,
        "win_method": session.state.win_method if session.finished else None,
        "victory_details": getattr(session.state, "b11_victory_details", None) if session.finished else None,
        "turn": view.turn_number,
        "position": view.position,
        "momentum": view.momentum,
        "human": {
            "name":own.wrestler.name, "power":view.own_power, "grip":list(view.own_grip),
            "hand":[{**enriched(card), "unavailable_reason":reason(i,card)} for i,card in enumerate(own.hand)],
            "draw_count":view.own_draw_count, "discard_count":view.own_discard_count,
            "discard":[shown_card(c) for c in own.discard_pile],
            "plays_remaining":view.plays_remaining,
            "kimarite":[shown_card(c) for c in own.kimarite_zone],
            "temporary":[shown_card(t.card) for t in own.temporary_zone],
        },
        "opponent": {
            "name":other.wrestler.name, "power":view.opponent_power,
            "grip":list(view.opponent_grip), "hand_count":view.opponent_hand_size,
            "draw_count":view.opponent_draw_count,"discard_count":view.opponent_discard_count,
            "discard":[shown_card(c) for c in other.discard_pile],
            "kimarite":[shown_card(c) for c in other.kimarite_zone],
            "temporary":[shown_card(t.card) for t in other.temporary_zone],
        },
        "selection": {
            "options":[enriched(c) for c in session.pending_selection.options],
            "keep":session.pending_selection.keep
        } if session.pending_selection else None,
        "legal_plays":[{"hand_index":x.hand_index,"card":asdict(x.card)} for x in session.actions()],
        "can_end_turn":session.awaiting_human and not session.finished and session.pending_selection is None,
    }


def dispatch(session: HumanBout, command: dict) -> dict:
    """UI command port. State is owned by session; consumers never mutate the engine."""
    if command["type"] == "choose_cards":
        session.choose_cards(command["indices"])
    elif command["type"] == "play_card":
        session.play(command["hand_index"], choices=command.get("choices"))
    elif command["type"] == "end_turn":
        session.end_turn()
    else:
        raise ValueError("Unknown UI command")
    return public_snapshot(session)
