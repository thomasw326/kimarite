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

from .b10_human_session import dispatch, new_b10_session, public_snapshot, roster
from .effects import ChoiceRequired, IllegalPlay

STATIC = Path(__file__).resolve().parents[2] / "web"
_sessions = {}
_lock = RLock()


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
        if path == "/api/roster":
            return self.reply(200, {"roster": roster()})
        if path.startswith("/api/session/"):
            token = path.removeprefix("/api/session/")
            with _lock:
                session = _sessions.get(token)
                return self.reply(200 if session else 404, public_snapshot(session) if session else {"error": "Unknown session"})
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
                if path == "/api/session":
                    if len(_sessions) >= 100:
                        return self.reply(503, {"error": "Session capacity reached"})
                    session = new_b10_session(data["human"], data["opponent"], seed=int(data.get("seed", 20261021)))
                    token = secrets.token_urlsafe(24)
                    _sessions[token] = session
                    return self.reply(201, {"token": token, "state":public_snapshot(session)})
                if path.startswith("/api/session/") and path.endswith("/action"):
                    token = path[len("/api/session/"):-len("/action")]
                    session = _sessions.get(token)
                    if not session:
                        return self.reply(404, {"error": "Unknown session"})
                    try:
                        snapshot = dispatch(session, data)
                        return self.reply(200, {"state":snapshot})
                    except ChoiceRequired as exc:
                        return self.reply(409, {"choice_required":True, "message":str(exc), "card":exc.card_name, "choice_name":exc.choice_name, "options":[{"value":option,"label":str(option)} for option in exc.options]})
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
