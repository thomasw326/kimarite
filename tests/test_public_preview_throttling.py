"""Public preview request throttling: bounded and concurrent safe.

Tests use the actual Handler for 429 behavior and the production limiter
under deterministic simulated timestamps. No slow sleeps and no live calls.
"""
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import json

import pytest

from kimarite import b10_web


@pytest.fixture(autouse=True)
def reset_limiter():
    with b10_web._lock:
        b10_web._rate_history.clear()
    yield
    with b10_web._lock:
        b10_web._rate_history.clear()


def test_sliding_window_allows_normal_drafting_and_expires_old_requests(monkeypatch):
    monkeypatch.setattr(b10_web, "MAX_POSTS_PER_CLIENT", 4)
    for i in range(4):
        with b10_web._lock:
            assert b10_web._allow_post("client-a", starting_bout=False, now=float(i))
    with b10_web._lock:
        assert not b10_web._allow_post("client-a", starting_bout=False, now=4.0)
        assert b10_web._allow_post("client-b", starting_bout=False, now=4.0)
        assert b10_web._allow_post("client-a", starting_bout=False, now=61.0)
        assert len(b10_web._rate_history["client-a", "post"]) == 3


def test_session_start_cap_does_not_block_other_normal_post_actions(monkeypatch):
    monkeypatch.setattr(b10_web, "MAX_BOUT_STARTS_PER_CLIENT", 2)
    monkeypatch.setattr(b10_web, "MAX_POSTS_PER_CLIENT", 10)
    with b10_web._lock:
        assert b10_web._allow_post("a", starting_bout=True, now=5)
        assert b10_web._allow_post("a", starting_bout=True, now=5)
        assert not b10_web._allow_post("a", starting_bout=True, now=5)
        assert b10_web._allow_post("a", starting_bout=False, now=5)
        assert len(b10_web._rate_history["a", "post"]) == 3
        assert len(b10_web._rate_history["a", "session"]) == 2


def test_limiting_is_atomic_under_parallel_workers(monkeypatch):
    monkeypatch.setattr(b10_web, "MAX_POSTS_PER_CLIENT", 20)
    monkeypatch.setattr(b10_web, "MAX_BOUT_STARTS_PER_CLIENT", 7)

    def invoke(_):
        with b10_web._lock:
            return b10_web._allow_post("shared", starting_bout=True, now=100.0)

    with ThreadPoolExecutor(max_workers=24) as executor:
        outcomes = list(executor.map(invoke, range(100)))
    assert sum(outcomes) == 7
    assert len(b10_web._rate_history["shared", "session"]) == 7
    assert len(b10_web._rate_history["shared", "post"]) == 7


def test_untrusted_forwarded_header_cannot_bypass_peer_rate_limit(monkeypatch):
    monkeypatch.setattr(b10_web, "MAX_POSTS_PER_CLIENT", 2)
    # do_POST must use client_address[0] rather than a forwarded identity.
    source = (b10_web.Path(__file__).resolve().parents[1] /
              "src" / "kimarite" / "b10_web.py").read_text()
    assert "_allow_post(self.client_address[0]" in source
    assert "X-Forwarded-For" not in source.split("def do_POST(self):", 1)[1]


@pytest.fixture
def http_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), b10_web.Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def send_post(base, path, data):
    req = Request(
        base + path, data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    return urlopen(req, timeout=10)


def test_real_http_429_is_json_with_retry_after(http_server, monkeypatch):
    monkeypatch.setattr(b10_web, "MAX_POSTS_PER_CLIENT", 2)
    for _ in range(2):
        with send_post(http_server, "/api/b11/draft/catalogue", {}) as reply:
            assert reply.status == 200
    with pytest.raises(HTTPError) as err:
        send_post(http_server, "/api/b11/draft/catalogue", {})
    assert err.value.code == 429
    assert err.value.headers.get("Retry-After") == "60"
    payload = json.load(err.value)
    assert payload["code"] == "rate_limited"
    assert "Retry" in payload["error"]
    # Read-only endpoints are still available.
    with urlopen(http_server + "/api/roster", timeout=10) as reply:
        assert reply.status == 200


def test_real_http_session_creation_limit_does_not_block_drafting(http_server, monkeypatch):
    monkeypatch.setattr(b10_web, "MAX_BOUT_STARTS_PER_CLIENT", 1)
    request = {"human": "Arm Controller", "opponent": "The Technician", "seed": 42}
    with send_post(http_server, "/api/session", request) as reply:
        assert reply.status == 201
    with pytest.raises(HTTPError) as err:
        send_post(http_server, "/api/session", request)
    assert err.value.code == 429
    with send_post(http_server, "/api/b11/draft/catalogue", {}) as reply:
        assert reply.status == 200


def test_rate_history_is_memory_bounded_under_many_peers(monkeypatch):
    monkeypatch.setattr(b10_web, "MAX_TRACKED_CLIENTS", 4)
    with b10_web._lock:
        for index in range(25):
            assert b10_web._allow_post(f"client-{index}", starting_bout=True, now=float(index))
        assert len(b10_web._rate_history) <= 8
