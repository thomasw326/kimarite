"""Real B12 AI-vs-AI matchday resolution.

The player's already-completed bout is the 21st result. Resolve the other
20 using the *same* Tachiai/Exchange rules and style_ai_v5 as the B12
60-framework big test; never estimate W/L from ranks, ratings or randomness.

Per-basho AI decks retain 28 different initial cards and one source-designated
duplicate per prior victory (maximum 12). In AI-only games, a hidden, rank-
based difficulty softly tunes non-core basics and optional V5 stat boosts.
The player's actual opponent continues using the original B12 deck and stats,
with the existing W/L-driven duplicate reward and adaptive matchmaking.
No future results are simulated before a player completes their own bout.
"""
from __future__ import annotations

from hashlib import sha256
import random

from .b12_division_roster import load_formats, validate_world
from .b12_difficulty import ai_difficulty, tuned_base_cards, tuned_stats
from .b12_league import MATCHES_PER_DAY, PLAYER, commit_day
from .catalog import card_by_name
from .models import BoutState, Card, FighterState, Side, Stat, Wrestler
from .style_ai_v5 import play_style_turn
from .styles_v5 import STYLES
from .tachiai import compare_tachiai, first_exchange_side
from .tachiai_effects import resolve_prepared_tachiai
from .turns import apply_initial_power, end_exchange_turn, start_exchange_turn

DEFAULT_MAX_TURNS = 100
MAX_DUPLICATES = 12


def ai_deck_names(framework: dict, prior_wins: int, *,
                  difficulty: int | None = None) -> list[str]:
    """28 originals + prior-win reward copies; optional NPC-only rank tuning.

    Difficulty=None is the exact original B12 player-opponent deck and must
    remain unchanged. AI-vs-AI alone supplies a rank-based difficulty.
    """
    if type(prior_wins) is not int or prior_wins < 0:
        raise ValueError("Prior wins must be a nonnegative integer")
    base = (framework["base"] if difficulty is None
            else tuned_base_cards(framework, difficulty))
    duplicates = framework["duplicates"]
    if len(base) != 28 or len(set(base)) != 28:
        raise ValueError("B12 AI framework must have 28 different base cards")
    if len(duplicates) != MAX_DUPLICATES or len(set(duplicates)) != MAX_DUPLICATES:
        raise ValueError("B12 AI framework must have 12 different reward copies")
    if not set(duplicates) <= set(base):
        raise ValueError("AI reward copies must belong to their starting deck")
    return [*base, *duplicates[:min(prior_wins, MAX_DUPLICATES)]]


def _physical_card(name: str) -> Card:
    c = card_by_name(name)
    # A fighter's duplicates must be different *physical* card objects.
    return Card(c.card_id, c.name, c.power, c.technique, c.spirit, c.is_kimarite)


def build_ai_fighter(wrestler: dict, framework: dict, seed: int, prior_wins: int,
                     *, difficulty: int | None = None) -> FighterState:
    """Same seeded opening rules; ranked tuning applies only if explicitly passed.

    The B12 player-versus-AI caller does not provide difficulty, preserving
    its established wrestler stats, exact framework and W/L earned copies.
    """
    if wrestler["format_id"] != framework["id"] or wrestler["style"] != framework["style_proxy"]:
        raise ValueError("The match wrestler does not own this unique framework")
    rng = random.Random(seed)
    cards = [_physical_card(name) for name in ai_deck_names(
        framework, prior_wins, difficulty=difficulty
    )]
    try:
        index = next(i for i, c in enumerate(cards) if c.name == framework["starting_kimarite"])
    except StopIteration as exc:
        raise ValueError("Starting Kimarite missing from B12 framework") from exc
    starting = cards.pop(index)
    if not starting.is_kimarite:
        raise ValueError("Starting Kimarite is not a finisher")
    ordinary = [c for c in cards if not c.is_kimarite]
    if len(ordinary) < 2:
        raise ValueError("Too few non-Kimarite opening cards")
    prepared = rng.choice(ordinary)
    cards = [c for c in cards if c is not prepared]
    top = rng.choice([c for c in cards if not c.is_kimarite and c.name != prepared.name])
    cards = [c for c in cards if c is not top]
    rng.shuffle(cards)
    profile = STYLES[wrestler["style"]]
    order = list(dict.fromkeys((profile.primary, profile.secondary)))
    order += [s.value for s in (Stat.POWER, Stat.TECHNIQUE, Stat.SPIRIT)
              if s.value not in order]
    stats = profile.stats if difficulty is None else tuned_stats(profile, difficulty)
    identity = Wrestler(wrestler["name"], *stats, starting, prepared, top,
                        primary=Stat(order[0]), secondary=Stat(order[1]),
                        tertiary=Stat(order[2]), ranking=wrestler["rank"])
    return FighterState(identity, draw_pile=[top, *cards],
                        kimarite_zone=[starting])


def match_seed(master: int, basho: int, day: int,
               left_id: str, right_id: str, format_id: str) -> int:
    """No process-random hash or ambient RNG; stable across save/reload."""
    if any(not isinstance(s, str) or not s for s in (left_id, right_id, format_id)):
        raise ValueError("Invalid stable match/format identity")
    data = f"b12-ai-bout-v1:{master}:{basho}:{day}:{left_id}:{right_id}:{format_id}"
    return int.from_bytes(sha256(data.encode("utf-8")).digest()[:8], "big")


def simulate_ai_bout(left: dict, right: dict, frameworks: dict[str, dict],
                     *, master_seed: int, basho: int, day: int,
                     max_turns: int = DEFAULT_MAX_TURNS) -> dict:
    """Fully play one AI-vs-AI bout; an incomplete result is a hard failure."""
    if type(max_turns) is not int or max_turns <= 0:
        raise ValueError("max_turns must be positive")
    a_id, b_id = left["id"], right["id"]
    if a_id == b_id or PLAYER in (a_id, b_id):
        raise ValueError("AI-only match requires two distinct AI identities")
    if left["format_id"] == right["format_id"]:
        raise ValueError("Two AI wrestlers cannot share a deck framework")
    a_seed = match_seed(master_seed, basho, day, a_id, b_id, left["format_id"])
    b_seed = match_seed(master_seed, basho, day, a_id, b_id, right["format_id"])
    # Only NPC-versus-NPC uses rank-weighted composition/stat difficulty.
    # Human-facing opponents continue to use the previously verified B12
    # construction and live W-L duplication rules, without this pyramid.
    a = build_ai_fighter(
        left, frameworks[left["format_id"]], a_seed, left["wins"],
        difficulty=ai_difficulty(master_seed, a_id, left["rank"])
    )
    b = build_ai_fighter(
        right, frameworks[right["format_id"]], b_seed, right["wins"],
        difficulty=ai_difficulty(master_seed, b_id, right["rank"])
    )
    state = BoutState(a, b)
    comp = compare_tachiai(a.wrestler, b.wrestler)
    try:
        apply_initial_power(state, comp)
        resolve_prepared_tachiai(state, comp)
        if state.winner is None:
            state.active_side = first_exchange_side(comp, a.wrestler, b.wrestler)
        for _ in range(max_turns):
            if state.winner is not None:
                break
            side = state.active_side
            if side not in (Side.A, Side.B):
                raise RuntimeError("No active wrestler for AI match")
            start_exchange_turn(state, side, comp)
            if state.winner is not None:
                break
            play_style_turn(state, side, comp,
                            left["style"] if side is Side.A else right["style"])
            if state.winner is not None:
                break
            end_exchange_turn(state, side)
    except (ValueError, KeyError, RuntimeError, NotImplementedError) as exc:
        raise RuntimeError(f"B12 AI match {a_id} vs {b_id} day {day+1} failed: {exc}") from exc
    if state.winner not in (Side.A, Side.B):
        raise RuntimeError(f"B12 AI match {a_id} vs {b_id} day {day+1} did not finish "
                           f"within {max_turns} turns")
    winner = a_id if state.winner is Side.A else b_id
    return {
        "a": a_id, "b": b_id, "winner": winner,
        "method": state.win_method, "source": state.win_source,
        "turns": state.turn_number,
        "format_a": left["format_id"], "format_b": right["format_id"],
        "deck_size_a": 28 + min(MAX_DUPLICATES, left["wins"]),
        "deck_size_b": 28 + min(MAX_DUPLICATES, right["wins"]),
        "seed_a": a_seed, "seed_b": b_seed,
    }


def commit_real_ai_matchday(roster: dict, league: dict, player_winner: str,
                            *, max_turns: int = DEFAULT_MAX_TURNS) -> tuple[dict, list[dict]]:
    """After the real player bout, simulate and commit the other 20 exactly once.

    The caller must already have scheduled the 21 matches and must provide
    the winner of the actual player-controlled bout. Only a fully successful
    20-bout simulation returns an updated ledger. Neither input is mutated.
    Never generate results from a win probability or replay them on reload.
    """
    validate_world(roster)
    if league.get("seed") != roster["seed"]:
        raise ValueError("Basho and roster seeds disagree")
    matches = league.get("pending_matches", [])
    if len(matches) != MATCHES_PER_DAY or len(league.get("results", [])) != league["day"]:
        raise ValueError("The player bout must belong to an already scheduled matchday")
    if matches[0][0] != PLAYER or player_winner not in matches[0]:
        raise ValueError("Expected the winner of this scheduled player's bout")
    current = {r["id"]: r for r in league["wrestlers"]}
    active = {w["wrestler_id"]: w for w in roster["wrestlers"]
              if w["division"] == "top"}
    if set(active) != set(current) - {PLAYER} or current[PLAYER]["rank"] != roster["player"]["rank"]:
        raise ValueError("Basho participants do not match the actual ranked roster")
    for wid, w in active.items():
        recorded = current[wid]
        if (recorded["format_id"], recorded["style"], recorded["name"], recorded["rank"]) != (
                w["format_id"], w["ai_style"], w["name"], w["rank"]):
            raise ValueError(f"AI identity or format changed during the basho: {wid}")
        if recorded["wins"] + recorded["losses"] != league["day"]:
            raise ValueError(f"AI record is not current at day {league['day']}: {wid}")
    if current[PLAYER]["wins"] + current[PLAYER]["losses"] != league["day"]:
        raise ValueError("Player record is not current")
    frameworks = {fmt["id"]: fmt for fmt in load_formats()}
    results = [{"a": matches[0][0], "b": matches[0][1], "winner": player_winner}]
    audit = []
    for left_id, right_id in matches[1:]:
        if PLAYER in (left_id, right_id):
            raise ValueError("Player appeared in an AI-only pairing")
        bout = simulate_ai_bout(current[left_id], current[right_id], frameworks,
                                master_seed=roster["seed"],
                                basho=roster.get("completed_basho", 0),
                                day=league["day"], max_turns=max_turns)
        audit.append(bout)
        results.append({"a": bout["a"], "b": bout["b"], "winner": bout["winner"]})
    if len(audit) != MATCHES_PER_DAY-1:
        raise RuntimeError("All 20 AI bouts must complete before committing matchday")
    updated = commit_day(league, results)  # 21 result validation, single atomic copy.
    updated.setdefault("ai_bout_audit", []).append(audit)
    return updated, audit
