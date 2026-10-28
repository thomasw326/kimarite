"""Minimal single-user localhost HTTP service for the B10 graphical bout UI.

Sessions exist only in this process. Bind to loopback, not a public interface.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import json
import secrets
from threading import RLock
from urllib.parse import urlsplit

from .b10_human_session import dispatch, new_b10_session, public_snapshot, roster, opening_options, management_deal
from .effects import ChoiceRequired, IllegalPlay
from .b11_pending_session import PendingB11Session

STATIC = Path(__file__).resolve().parents[2] / "web"
_sessions = {}
_lock = RLock()



def labelled_choices(session, exc, command=None):
    """Show names for indexed public/chooser-visible cards, without exposing hidden hands."""
    own = session.state.fighter(session.human_side)
    foe = session.state.opponent(session.human_side)
    key = exc.choice_name
    card_name = exc.card_name
    titles = {
        "hand_index": "Choose a card from your hand",
        "discard_index": "Choose a card from your discard pile",
        "sacrifice_kimarite": "Choose a Kimarite to sacrifice",
        "temporary_index": "Choose an opponent Temporary to disrupt",
        "uwate_card_index": "Choose a revealed card",
        "hikiotoshi_card_index": "Choose one of the top three cards to keep",
        "opponent_deck_index": "Choose a revealed opponent deck card to discard",
        "opponent_hand_index": "Choose a position in opponent's hidden hand",
        "card_target": "Choose an opponent Grip-related card to remove",
        "grip": "Choose Left or Right Grip",
        "mode": "Choose an effect",
        "use_optional": "Use the optional effect?",
        "cycle_if_no_grip": "Draw and discard a card?",
        "discard_for_grip": "Discard a card to establish Left Grip?",
    }
    title = titles.get(key, "Choose an option")
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
                cards = own.hand[:]
                played_index = (command or {}).get("hand_index")
                if isinstance(played_index, int) and 0 <= played_index < len(cards):
                    cards.pop(played_index)
                # Pull resolves its draw before the discard choice. The
                # original session is transactional, so expose the drawn card
                # from the top of the unchanged draw pile in the right slot.
                if card_name == "Pull" and own.draw_pile:
                    cards.append(own.draw_pile[0])
            elif key == "discard_index":
                cards = own.discard_pile
            elif key == "sacrifice_kimarite":
                cards = own.kimarite_zone
            elif key == "temporary_index":
                cards = [entry.card for entry in foe.temporary_zone]
            elif key == "opponent_deck_index":
                cards = foe.draw_pile[:3]
            elif key == "uwate_card_index":
                cards = own.draw_pile[:max(0, own.total_grip)]
            elif key == "hikiotoshi_card_index":
                cards = own.draw_pile[:3]
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
                label = f"Option {option + 1}"
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
            }
            label = modes.get(str(option), str(option).replace("_", " ").title())
        item = {"value": option, "label": label}
        if selected_card is not None:
            item["card"] = card_info(selected_card)
        options.append(item)
    return {"choice_required": True, "message": str(exc), "card": card_name,
            "choice_name": key, "choice_title": title, "options": options}

class Handler(BaseHTTPRequestHandler):
    def reply(self, code: int, payload: dict):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= 32768:
            raise ValueError("Invalid request size")
        return json.loads(self.rfile.read(length))

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
                session = _sessions.get(token)
                return self.reply(200 if session else 404, (session.snapshot() if isinstance(session, PendingB11Session) else public_snapshot(session)) if session else {"error": "This bout expired because the game server restarted. Start a new bout.", "code":"session_expired"})
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
        try:
            data = self.body()
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
                    from .b11_player_draft import grow_deck, deal_block
                    deck, ids = grow_deck(data["starting_cards"], data["picks"], int(data["draft_seed"]),
                                          data.get("duplicated_indices", []))
                    return self.reply(200, {"cards": deal_block(deck, int(data["seed"]), ids),
                                            "deck_size": len(deck)})
                if path == "/api/session":
                    if len(_sessions) >= 100:
                        return self.reply(503, {"error": "Session capacity reached"})
                    if data.get("opening_mode") in {"b11_preview", "b11_live"}:
                        drafted = None
                        if "draft_picks" in data:
                            from .b11_player_draft import grow_deck
                            drafted, _ = grow_deck(data["starting_cards"], data["draft_picks"],
                                                   int(data["draft_seed"]), data.get("duplicated_indices", []))
                        session = PendingB11Session.start(data["human"], data["opponent"], data["opening_cards"], seed=int(data.get("seed", 20261021)), created_stats=data.get("created_stats"), drafted_deck=drafted)
                        session.live_enabled = data.get("opening_mode") == "b11_live"
                    else:
                        session = new_b10_session(data["human"], data["opponent"], seed=int(data.get("seed", 20261021)), opening=data.get("opening"))
                    token = secrets.token_urlsafe(24)
                    _sessions[token] = session
                    return self.reply(201, {"token": token, "state":session.snapshot() if isinstance(session, PendingB11Session) else public_snapshot(session)})
                if path.startswith("/api/session/") and path.endswith("/action"):
                    token = path[len("/api/session/"):-len("/action")]
                    session = _sessions.get(token)
                    if not session:
                        return self.reply(404, {"error": "Bout expired on server restart.", "code": "session_expired"})
                    if isinstance(session, PendingB11Session):
                        if data.get("type") == "commit_tachiai":
                            if not session.phase.pending:
                                return self.reply(409, {"error": "Tachiai is already committed.", "code": "tachiai_already_committed", "state": session.snapshot()})
                            committed_snapshot = session.confirm(data["indices"])
                            if getattr(session, "live_enabled", False):
                                from .b11_live_opening import start_b11_human_bout
                                live = start_b11_human_bout(session)
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
