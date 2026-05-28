import logging

import httpx
import pytest

from core.http import HttpClient


def test_get_succeeds_on_200(httpx_mock):
    httpx_mock.add_response(method="GET", url="https://example.test/ok", json={"ok": True})
    client = HttpClient(base_url="https://example.test")
    r = client.get("/ok")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_retries_on_429_then_succeeds(httpx_mock):
    httpx_mock.add_response(
        method="GET", url="https://example.test/x", status_code=429, headers={"Retry-After": "0"}
    )
    httpx_mock.add_response(method="GET", url="https://example.test/x", json={"ok": True})
    client = HttpClient(base_url="https://example.test", max_retries=3, backoff_base=0.0)
    r = client.get("/x")
    assert r.status_code == 200


def test_retries_on_5xx_then_succeeds(httpx_mock):
    httpx_mock.add_response(method="GET", url="https://example.test/y", status_code=503)
    httpx_mock.add_response(method="GET", url="https://example.test/y", status_code=502)
    httpx_mock.add_response(method="GET", url="https://example.test/y", json={"ok": True})
    client = HttpClient(base_url="https://example.test", max_retries=5, backoff_base=0.0)
    r = client.get("/y")
    assert r.status_code == 200


def test_gives_up_after_max_retries(httpx_mock):
    for _ in range(4):
        httpx_mock.add_response(method="GET", url="https://example.test/z", status_code=503)
    client = HttpClient(base_url="https://example.test", max_retries=3, backoff_base=0.0)
    with pytest.raises(httpx.HTTPStatusError):
        client.get("/z")


def test_authorization_header_is_redacted_in_logs(httpx_mock, caplog):
    httpx_mock.add_response(method="GET", url="https://example.test/a", json={"ok": True})
    client = HttpClient(
        base_url="https://example.test", default_headers={"Authorization": "Bearer SECRET"}
    )
    with caplog.at_level(logging.INFO, logger="ecom.http"):
        client.get("/a")
    log_text = "\n".join(r.message for r in caplog.records)
    assert "SECRET" not in log_text
