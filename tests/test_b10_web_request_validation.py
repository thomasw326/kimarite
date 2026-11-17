"""The public preview must fail safely on malformed or cross-site simple POSTs."""
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import json

import pytest

from kimarite.b10_web import Handler


@pytest.fixture
def app_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def post(base, content: bytes, content_type: str):
    return urlopen(Request(
        base + "/api/b11/draft/catalogue",
        data=content, method="POST",
        headers={"Content-Type": content_type},
    ), timeout=10)


@pytest.mark.parametrize("content,content_type,error", [
    (b"{}", "text/plain", "Content-Type must be application/json"),
    (b"{}", "application/x-www-form-urlencoded", "Content-Type must be application/json"),
    (b"[]", "application/json", "Expected a JSON object"),
    (b"null", "application/json", "Expected a JSON object"),
    (b"42", "application/json", "Expected a JSON object"),
    (b"not-json", "application/json", "Expecting value"),
])
def test_bad_post_bodies_are_rejected_cleanly(app_url, content, content_type, error):
    with pytest.raises(HTTPError) as exc:
        post(app_url, content, content_type)
    assert exc.value.code == 400
    response = json.load(exc.value)
    assert error in response["error"]


@pytest.mark.parametrize("content_type", ["application/json", "application/json; charset=utf-8"])
def test_normal_json_requests_continue_to_work(app_url, content_type):
    with post(app_url, b"{}", content_type) as response:
        assert response.status == 200
        payload = json.load(response)
    assert len(payload["kimarite_names"]) >= 3
