"""Public-preview process sessions expire; active bouts refresh, capacity stays bounded."""
import json
import time
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from kimarite import b10_web


def isolate_sessions(fn):
    """Restore global sessions after exercising lifecycle invariants."""
    with b10_web._lock:
        original_sessions = b10_web._sessions.copy()
        original_activity = b10_web._session_activity.copy()
        b10_web._sessions.clear()
        b10_web._session_activity.clear()
    try:
        return fn()
    finally:
        with b10_web._lock:
            b10_web._sessions.clear()
            b10_web._sessions.update(original_sessions)
            b10_web._session_activity.clear()
            b10_web._session_activity.update(original_activity)


def test_idle_sessions_prune_but_active_sessions_remain():
    def check():
        with b10_web._lock:
            b10_web._sessions.update(stale=object(), active=object())
            b10_web._session_activity.update(
                stale=10_000-b10_web.SESSION_IDLE_SECONDS-1,
                active=9_999,
                ghost=9_999,
            )
            b10_web._prune_sessions(10_000)
            assert "stale" not in b10_web._sessions
            assert "stale" not in b10_web._session_activity
            assert "ghost" not in b10_web._session_activity
            assert "active" in b10_web._sessions
            b10_web._touch_session("active", 10_001)
            assert b10_web._session_activity["active"] == 10_001
            b10_web._prune_sessions(10_000+b10_web.SESSION_IDLE_SECONDS)
            assert "active" in b10_web._sessions
    isolate_sessions(check)


def test_legacy_direct_session_insert_gets_valid_activity():
    def check():
        with b10_web._lock:
            b10_web._sessions["legacy"] = object()
            b10_web._prune_sessions(55)
            assert b10_web._session_activity["legacy"] == 55
    isolate_sessions(check)


def test_idle_session_expires_in_http_route_and_reports_recoverable_code():
    def check():
        server = ThreadingHTTPServer(("127.0.0.1", 0), b10_web.Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            payload = json.dumps({
                "human": "Arm Controller", "opponent": "The Technician", "seed": 20261117
            }).encode()
            with urlopen(Request(base+"/api/session", payload,
                                 {"Content-Type": "application/json"}, method="POST"), timeout=15) as r:
                data = json.load(r)
                token = data["token"]
            with b10_web._lock:
                b10_web._session_activity[token] = time.monotonic()-b10_web.SESSION_IDLE_SECONDS-2
            try:
                urlopen(base+"/api/session/"+token, timeout=15)
                raise AssertionError("Expired sessions must not resolve")
            except HTTPError as err:
                assert err.code == 404
                assert json.load(err)["code"] == "session_expired"
            with b10_web._lock:
                assert token not in b10_web._sessions
                assert token not in b10_web._session_activity
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
    isolate_sessions(check)


def test_capacity_prunes_abandoned_sessions_before_rejecting_new_bout():
    def check():
        now = time.monotonic()
        with b10_web._lock:
            for index in range(b10_web.MAX_SESSIONS):
                token = f"idle-{index}"
                b10_web._sessions[token] = object()
                b10_web._session_activity[token] = now-b10_web.SESSION_IDLE_SECONDS-5
            assert len(b10_web._sessions) == b10_web.MAX_SESSIONS
        server = ThreadingHTTPServer(("127.0.0.1", 0), b10_web.Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            body = json.dumps({
                "human": "Arm Controller", "opponent": "The Technician", "seed": 42
            }).encode()
            request = Request(f"http://127.0.0.1:{server.server_port}/api/session",body,
                              {"Content-Type":"application/json"},method="POST")
            with urlopen(request, timeout=15) as response:
                assert response.status == 201
                token=json.load(response)["token"]
            with b10_web._lock:
                assert len(b10_web._sessions) == 1
                assert token in b10_web._session_activity
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
    isolate_sessions(check)
