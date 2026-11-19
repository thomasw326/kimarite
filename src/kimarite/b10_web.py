"""Single-origin HTTP interface for the browser game and its Python rules engine.

Live bout sessions are process-local and expire after inactivity. A separate
browser-local command journal can replay an expired bout; this is still a
prototype server, not production multi-tenant infrastructure.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import json
import secrets
import time
from threading import RLock
from collections import deque
from urllib.parse import urlsplit

from .b10_human_session import dispatch, new_b10_session, public_snapshot, roster, opening_options, management_deal
from .effects import ChoiceRequired, IllegalPlay
from .b11_pending_session import PendingB11Session
from .tutorial_bout import TutorialOpening

STATIC = Path(__file__).resolve().parents[2] / "web"
_sessions = {}
_session_activity: dict[str, float] = {}
_lock = RLock()
MAX_SESSIONS = 100
# Inactivity, rather than a hard bout duration: the browser journal permits
# recovery if the service restarts or a long-idle session expires.
SESSION_IDLE_SECONDS = 60 * 60

# Preview-only throttling. The peer address comes from the socket, never a
# client-controlled X-Forwarded-For header.
RATE_WINDOW_SECONDS = 60
MAX_POSTS_PER_CLIENT = 180
MAX_BOUT_STARTS_PER_CLIENT = 24
MAX_TRACKED_CLIENTS = 2048
_rate_history: dict[tuple[str, str], deque[float]] = {}


def _allow_post(client: str, *, starting_bout: bool, now: float | None = None) -> bool:
    """Sliding window limiter; caller must hold _lock."""
    if now is None:
        now = time.monotonic()
    for key, history in list(_rate_history.items()):
        while history and now - history[0] >= RATE_WINDOW_SECONDS:
            history.popleft()
        if not history:
            del _rate_history[key]
    rules = [(client, "post", MAX_POSTS_PER_CLIENT)]
    if starting_bout:
        rules.append((client, "session", MAX_BOUT_STARTS_PER_CLIENT))
    if any(len(_rate_history.get((ip, kind), ())) >= limit for ip, kind, limit in rules):
        return False
    for ip, kind, _ in rules:
        _rate_history.setdefault((ip, kind), deque()).append(now)
    # Bounded memory even with many distinct socket peers.
    if len(_rate_history) > MAX_TRACKED_CLIENTS * 2:
        oldest = sorted(_rate_history, key=lambda k: _rate_history[k][-1])
        for key in oldest[:len(_rate_history) - MAX_TRACKED_CLIENTS * 2]:
            del _rate_history[key]
    return True


def _prune_sessions(now: float | None = None) -> None:
    """Expire idle sessions and remove stale metadata; caller holds _lock."""
    if now is None:
        now = time.monotonic()
    for token, touched in list(_session_activity.items()):
        if token not in _sessions or now - touched > SESSION_IDLE_SECONDS:
            _sessions.pop(token, None)
            _session_activity.pop(token, None)
    # Legacy test fixtures sometimes insert directly into _sessions.
    for token in _sessions:
        _session_activity.setdefault(token, now)


def _touch_session(token: str, now: float | None = None) -> None:
    """A valid session request prolongs its inactivity window."""
    if token in _sessions:
        _session_activity[token] = time.monotonic() if now is None else now




def labelled_choices(session, exc, command=None):
    """Show names for indexed public/chooser-visible cards, without exposing hidden hands."""
    own = session.state.fighter(session.human_side)
    foe = session.state.opponent(session.human_side)
    key = exc.choice_name
    card_name = exc.card_name
    titles = {
        "hand_index": "Choose a card from your hand",
        "discard_index": "Choose a card from your discard pile",
        "replay_discard_index": "Choose a discarded card to play, then Exhaust",
        "sacrifice_kimarite": "Choose a Kimarite to sacrifice",
        "temporary_index": "Choose an opponent Temporary to disrupt",
        "uwate_card_index": "Choose a revealed card",
        "hikiotoshi_card_index": "Choose one of the top three cards to keep",
        "utchari_card_index": "Choose one of the top two cards to keep",
        "opponent_deck_index": "Choose a revealed opponent deck card to discard",
        "opponent_hand_index": "Choose a position in opponent's hidden hand",
        "card_target": "Choose an opponent Grip-related card to remove",
        "grip": "Choose Left or Right Grip",
        "mode": "Choose an effect",
        "use_optional": "Use the optional effect?",
        "cycle_if_no_grip": "Draw and discard a card?",
        "discard_for_grip": "Discard a card to establish Left Grip?",
    }
    title = titles.get(key, "Choose a discarded card to play, then Exhaust" if key.startswith("replay_discard_index") else "Choose an option")
    # Name the CONSEQUENCE, not only the source zone. For example, Oshi's
    # hand_index is a discard cost, not another card-play selection.
    action_help = {
        "hand_index": ("Discard", "Choose one card to DISCARD from your hand. You are not playing the selected card."),
        "discard_index": ("Recover", "Choose one card to RETURN from your discard pile to your hand."),
        "sacrifice_kimarite": ("Sacrifice", "Choose a Kimarite to REMOVE from your Kimarite Zone and put in your discard pile."),
        "temporary_index": ("Remove", "Choose an opponent Temporary to REMOVE from their active zone."),
        "uwate_card_index": ("Play", "Choose which revealed card to PLAY with this effect."),
        "hikiotoshi_card_index": ("Keep", "Choose which of the revealed top cards to KEEP. The others go to the bottom of your deck."),
        "utchari_card_index": ("Keep", "Choose which of the revealed top cards to KEEP. The others go to the bottom of your deck."),
        "opponent_deck_index": ("Discard", "Choose which revealed card to DISCARD from your opponent's deck."),
        "opponent_hand_index": ("Discard", "Choose one position to DISCARD from your opponent's hidden hand. Card names remain hidden."),
        "card_target": ("Remove", "Choose an opponent card to REMOVE from its active zone."),
        "grip": ("Reduce", "Choose which of your opponent's Grips to REDUCE."),
        "mode": ("Use", "Choose the effect to resolve."),
        "use_optional": ("Choose", "Choose Yes to use the optional effect, or No to skip it."),
        "cycle_if_no_grip": ("Choose", "Yes: draw a card, then discard one card from your hand. No: skip."),
        "discard_for_grip": ("Choose", "Yes: discard one card from your hand to establish Left Grip. No: skip."),
    }
    if key.startswith("replay_discard_index"):
        verb, help_text = "Play & Exhaust", "Choose a card from your discard pile to PLAY, then Exhaust after resolving its effects."
    else:
        verb, help_text = action_help.get(key, ("Choose", "Choose one of the available options to resolve this card."))
    if key == "hand_index":
        title = "Choose 1 card to DISCARD from your hand"
    elif key == "discard_index":
        title = "Choose 1 discarded card to RETURN to your hand"
    elif key == "grip":
        title = "Choose which opponent Grip to REDUCE"
    elif key == "opponent_hand_index":
        title = "Choose an opponent's hidden hand position to DISCARD"
    elif key == "uwate_card_index":
        title = "Choose a revealed card to PLAY"
    if card_name == "Hatakikomi" and key == "use_optional":
        help_text = "Yes: lose 1 Momentum, then discard a card from your opponent's hand (or draw if their hand is empty). No: skip."
    from .b10_card_info import card_info
    options = []
    for option in exc.options:
        label = str(option)
        selected_card = None
        if isinstance(option, bool):
            if key == "use_optional" and card_name == "Kirikaeshi":
                label = "Lose 1 Power, gain 1 Momentum, draw 1" if option else "Skip optional effect"
            else:
                label = "Yes" if option else "No"
        elif isinstance(option, int) and not isinstance(option, bool):
            cards = None
            if key == "hand_index":
                cards = getattr(exc, "visible_cards", None)
                if cards is None:
                    # Legacy direct calls may not include a transactional
                    # preview. Do not guess that a newly drawn card occupies
                    # an existing hand slot.
                    cards = own.hand[:]
                    played_index = (command or {}).get("hand_index")
                    if isinstance(played_index, int) and 0 <= played_index < len(cards):
                        cards.pop(played_index)
                    if card_name == "Pull" and own.draw_pile:
                        cards.append(own.draw_pile[0])
            elif key == "discard_index" or key.startswith("replay_discard_index"):
                cards = getattr(exc, "visible_cards", own.discard_pile)
            elif key == "sacrifice_kimarite":
                cards = getattr(exc, "visible_cards", own.kimarite_zone)
            elif key == "temporary_index":
                cards = [entry.card for entry in foe.temporary_zone]
            elif key == "opponent_deck_index":
                cards = foe.draw_pile[:3]
            elif key == "uwate_card_index":
                cards = own.draw_pile[:max(0, own.total_grip)]
            elif key == "hikiotoshi_card_index":
                cards = own.draw_pile[:3]
            elif key == "utchari_card_index":
                cards = own.draw_pile[:2]
            elif key == "card_target":
                from .effects import GRIP_REFERENCING_TEMPORARIES, GRIP_REFERENCING_KIMARITE
                cards = [t.card for t in foe.temporary_zone if t.card.name in GRIP_REFERENCING_TEMPORARIES]
                cards += [c for c in foe.kimarite_zone if c.name in GRIP_REFERENCING_KIMARITE]
            if cards is not None and 0 <= option < len(cards):
                selected_card = cards[option]
                label = f"{option + 1}. {selected_card.name}"
            elif key == "opponent_hand_index":
                label = f"Opponent hand position {option + 1} (hidden card)"
            else:
                label = f"Card position {option + 1} (name unavailable)" if key == "hand_index" else f"Option {option + 1}"
        elif key == "grip":
            label = f"{str(option).title()} Grip"
        elif key == "mode":
            modes = {
                "draw": "Draw 1 card", "remove": "Remove a Temporary",
                "reduce_grip": "Reduce opponent Grip", "remove_card": "Remove opponent card",
                "grip": "Reduce opponent Grip", "temporary": "Disrupt a Temporary",
                "power_payoff": "Gain 1 Push and 1 Momentum",
                "power_crusher": "Gain Momentum; opponent loses Power",
                "power": "Gain 1 Power", "momentum": "Gain 1 Momentum",
                "grip": "Improve your shallower Grip",
            }
            label = modes.get(str(option), str(option).replace("_", " ").title())
        item = {"value": option, "label": label}
        if selected_card is not None:
            item["card"] = card_info(selected_card)
        options.append(item)
    return {"choice_required": True, "message": str(exc), "card": card_name,
            "choice_name": key, "choice_title": title, "choice_verb": verb,
            "choice_help": help_text, "options": options}

class Handler(BaseHTTPRequestHandler):
    def reply(self, code: int, payload: dict):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        if code == 429:
            self.send_header("Retry-After", str(RATE_WINDOW_SECONDS))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        # The browser uses JSON POSTs. Reject text/plain form submissions,
        # which could otherwise send simple cross-site requests without CORS
        # preflight, and reject non-object JSON before any handler mutates state.
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise ValueError("Content-Type must be application/json")
        length = int(self.headers.get("Content-Length", "0"))
        max_length = 262144 if urlsplit(self.path).path.startswith("/api/b12/campaign/") else 32768
        if not 0 < length <= max_length:
            raise ValueError("Invalid request size")
        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON object")
        return payload

    def do_GET(self):
        path = urlsplit(self.path).path
        if path.startswith("/api/management/deal/"):
            from urllib.parse import unquote, parse_qs
            try:
                name = unquote(path.removeprefix("/api/management/deal/"))
                seed = int(parse_qs(urlsplit(self.path).query).get("seed", ["20261021"])[0])
                return self.reply(200, management_deal(name, seed))
            except (ValueError, TypeError) as exc:
                return self.reply(400, {"error": str(exc)})
        if path == "/api/shikona":
            # One canonical fictional-name pool serves the player picker and
            # the future 60-wrestler campaign. Never return real-wrestler names.
            from .b12_division_roster import load_shikona
            return self.reply(200, {"names": load_shikona()})
        if path == "/api/roster":
            return self.reply(200, {"roster": roster()})
        if path.startswith("/api/opening/"):
            from urllib.parse import unquote
            try:
                return self.reply(200, opening_options(unquote(path.removeprefix("/api/opening/"))))
            except ValueError as exc:
                return self.reply(404, {"error":str(exc)})
        if path.startswith("/api/session/"):
            token = path.removeprefix("/api/session/")
            with _lock:
                _prune_sessions()
                session = _sessions.get(token)
                if session is not None:
                    _touch_session(token)
                return self.reply(200 if session else 404, (session.snapshot() if isinstance(session, PendingB11Session) else public_snapshot(session)) if session else {"error": "Bout session expired or the server restarted. Your browser can attempt recovery.", "code":"session_expired"})
        if path in ("/", "/index.html", "/client.js", "/style.css"):
            data = (STATIC / ("client.js" if path == "/client.js" else "style.css" if path == "/style.css" else "index.html")).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript; charset=utf-8" if path == "/client.js" else "text/css; charset=utf-8" if path == "/style.css" else "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return self.wfile.write(data)
        self.reply(404, {"error": "Not found"})

    def do_POST(self):
        path = urlsplit(self.path).path
        # Protect costly endpoints before reading the body, atomically with
        # other workers through the session lock.
        with _lock:
            allowed = _allow_post(self.client_address[0], starting_bout=path == "/api/session")
        if not allowed:
            return self.reply(429, {
                "error": "Too many requests from this connection. Retry shortly.",
                "code": "rate_limited",
            })
        try:
            data = self.body()
            # The 20 real AI bouts can take several seconds. Never hold the
            # process-global human-session lock while computing their results.
            if path.startswith("/api/b12/campaign/"):
                from .b12_campaign_web import campaign_request
                session = None
                resolve_lock = None
                if path in ("/api/b12/campaign/resolve", "/api/b12/campaign/playoff/resolve"):
                    from threading import Lock
                    with _lock:
                        _prune_sessions()
                        session = _sessions.get(data.get("token"))
                        if session is not None:
                            _touch_session(data["token"])
                            if not hasattr(session, "b12_resolve_lock"):
                                session.b12_resolve_lock = Lock()
                            resolve_lock = session.b12_resolve_lock
                try:
                    if resolve_lock is not None:
                        # Only one resolution per player-bout token; different
                        # browser sessions are free to play in parallel.
                        with resolve_lock:
                            result = campaign_request(path, data, session=session)
                    else:
                        result = campaign_request(path, data, session=session)
                    return self.reply(200, result)
                except (KeyError, ValueError, TypeError, RuntimeError) as exc:
                    return self.reply(409, {"error": str(exc), "code": "campaign_conflict"})
            with _lock:
                if path == "/api/b11/draft/catalogue":
                    from .b11_player_draft import AVAILABLE
                    return self.reply(200, {"kimarite_names": sorted(name for name, card in AVAILABLE.items() if card.is_kimarite)})
                if path == "/api/b11/draft/offer":
                    from .b11_player_draft import options_for, AVAILABLE
                    from .b10_card_info import card_info
                    choices = options_for(data["starting_cards"], data["picks"], int(data["seed"]))
                    return self.reply(200, {"choices": [card_info(AVAILABLE[n]) for n in choices]})
                if path == "/api/b11/draft/deal":
                    from .b11_player_draft import grow_deck, deal_block, remove_from_deck
                    deck, ids = grow_deck(data["starting_cards"], data["picks"], int(data["draft_seed"]),
                                          data.get("duplicated_indices", []))
                    deck, ids = remove_from_deck(deck, ids, data.get("excluded_ids", []))
                    return self.reply(200, {"cards": deal_block(
                        deck, int(data["seed"]), ids, guaranteed=data.get("guaranteed_ids", []),
                        previous=data.get("previous_ids", [])),
                                            "deck_size": len(deck)})
                if path == "/api/session":
                    _prune_sessions()
                    if len(_sessions) >= MAX_SESSIONS:
                        return self.reply(503, {"error": "Session capacity reached; retry later."})
                    if data.get("opening_mode") == "tutorial":
                        session = TutorialOpening.new()
                    elif data.get("opening_mode") in {"b11_preview", "b11_live"}:
                        drafted = None
                        if "draft_picks" in data:
                            from .b11_player_draft import grow_deck, remove_from_deck
                            drafted, ids = grow_deck(data["starting_cards"], data["draft_picks"],
                                                   int(data["draft_seed"]), data.get("duplicated_indices", []))
                            drafted, _ = remove_from_deck(drafted, ids, data.get("excluded_ids", []))
                        session = PendingB11Session.start(data["human"], data["opponent"], data["opening_cards"], seed=int(data.get("seed", 20261021)), created_stats=data.get("created_stats"), drafted_deck=drafted, opponent_ai=data.get("b12_opponent_ai"), player_rank=data.get("b12_player_rank", 1))
                        session.live_enabled = data.get("opening_mode") == "b11_live"
                        if "b12_campaign" in data:
                            if data.get("opening_mode") != "b11_live" or session.opponent_ai is None:
                                raise ValueError("B12 match requires a live drafted bout")
                            meta = data["b12_campaign"]
                            if not isinstance(meta, dict) or any(type(meta.get(k)) is not int for k in ("seed", "basho", "day")) or not isinstance(meta.get("opponent_id"), str) or meta["opponent_id"] != session.opponent_ai["id"]:
                                raise ValueError("B12 world match identity is malformed")
                            session.b12_campaign = meta
                        interview = data.get("b12_interview")
                        if interview is not None:
                            if not hasattr(session, "b12_campaign") or not isinstance(interview, dict):
                                raise ValueError("Interview rewards require a B12 campaign bout.")
                            kind = interview.get("kind")
                            if kind == "stack":
                                name = interview.get("card")
                                if not isinstance(name, str) or drafted is None or name not in drafted:
                                    raise ValueError("Interview top card must be in the deck.")
                            elif kind not in {"power", "technique", "spirit", "double_dip", "stamina"}:
                                raise ValueError("Unknown bout interview reward.")
                            session.interview = interview
                        rematch_card = data.get("b12_rematch_top_card")
                        if rematch_card is not None:
                            from .catalog import card_by_name
                            if not hasattr(session, "b12_campaign") or not isinstance(rematch_card, str):
                                raise ValueError("A rematch top card requires a B12 campaign bout.")
                            session.rematch_top_card = card_by_name(rematch_card)
                    else:
                        session = new_b10_session(data["human"], data["opponent"], seed=int(data.get("seed", 20261021)), opening=data.get("opening"))
                    token = secrets.token_urlsafe(24)
                    _sessions[token] = session
                    _touch_session(token)
                    return self.reply(201, {"token": token, "state":session.snapshot() if isinstance(session, PendingB11Session) else public_snapshot(session)})
                if path.startswith("/api/session/") and path.endswith("/action"):
                    token = path[len("/api/session/"):-len("/action")]
                    _prune_sessions()
                    session = _sessions.get(token)
                    if not session:
                        return self.reply(404, {"error": "Bout expired or the server restarted; recover from your browser's saved actions.", "code": "session_expired"})
                    _touch_session(token)
                    if isinstance(session, PendingB11Session):
                        if data.get("type") == "commit_tachiai":
                            if not session.phase.pending:
                                return self.reply(409, {"error": "Tachiai is already committed.", "code": "tachiai_already_committed", "state": session.snapshot()})
                            committed_snapshot = session.confirm(data["indices"])
                            if isinstance(session, TutorialOpening):
                                live = session.start_bout()
                                _sessions[token] = live
                                return self.reply(200, {"state": public_snapshot(live)})
                            if getattr(session, "live_enabled", False):
                                from .b11_live_opening import start_b11_human_bout
                                live = start_b11_human_bout(session)
                                if hasattr(session, "b12_campaign"):
                                    live.b12_campaign = session.b12_campaign
                                _sessions[token] = live
                                return self.reply(200, {"state": public_snapshot(live)})
                            return self.reply(200, {"state": committed_snapshot})
                        return self.reply(409, {"error": "B11 live resolution is not yet enabled.", "code": "b11_preview_only", "state": session.snapshot()})
                    try:
                        snapshot = dispatch(session, data)
                        return self.reply(200, {"state":snapshot})
                    except IllegalPlay as exc:
                        return self.reply(409, {"error": str(exc), "code": "invalid_action", "state": public_snapshot(session)})
                    except ChoiceRequired as exc:
                        return self.reply(409, labelled_choices(session, exc, data))
            return self.reply(404, {"error": "Not found"})
        except (KeyError, ValueError, TypeError, IllegalPlay) as exc:
            return self.reply(400, {"error":str(exc)})


def main():
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")))
    p.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    args = p.parse_args()
    print(f"B10 browser bout listening on {args.host}:{args.port}", flush=True)
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
