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


def test_redacting_filter_blanks_lines_containing_bearer_token(caplog):
    from core.http import _log  # noqa: PLC2701 - intentional, testing redaction

    with caplog.at_level(logging.INFO, logger="ecom.http"):
        _log.info("Authorization: Bearer abc123xyz secret")
    rendered = "\n".join(r.getMessage() for r in caplog.records)
    assert "abc123xyz" not in rendered
    assert "[redacted sensitive log line]" in rendered


def test_redacting_filter_does_not_false_positive_on_cursor_tokens(caplog):
    from core.http import _log  # noqa: PLC2701

    cursor = "eyJsYXN0X2lkIjoxMjN9"  # gitleaks:allow - synthetic base64, not a secret
    with caplog.at_level(logging.INFO, logger="ecom.http"):
        _log.info("pagination cursor token=%s (not a secret)", cursor)
    rendered = "\n".join(r.getMessage() for r in caplog.records)
    # The legitimate cursor should remain visible (was false-positive-redacted before).
    assert cursor in rendered


def test_redacting_filter_blanks_token_header_dump_with_colon_space(caplog):
    from core.http import _log  # noqa: PLC2701

    secret = "shpat_secretvalue123"  # gitleaks:allow - synthetic test fixture
    with caplog.at_level(logging.INFO, logger="ecom.http"):
        _log.info("response headers: Token: %s", secret)
    rendered = "\n".join(r.getMessage() for r in caplog.records)
    assert secret not in rendered
    assert "[redacted sensitive log line]" in rendered
