"""HTTP client with retry/backoff/redacting logs. Every domain client builds on this."""

from __future__ import annotations

import logging
import random
import time
from typing import Any

import httpx

from core.logging import get_logger

_log = get_logger("ecom.http")

_RETRY_STATUSES = {429, 500, 502, 503, 504}


class HttpClient:
    """Thin httpx.Client wrapper with retry, backoff, and log redaction.

    Subclass per domain (e.g. ShopifyClient) and add high-level methods.
    """

    def __init__(
        self,
        *,
        base_url: str = "",
        default_headers: dict[str, str] | None = None,
        max_retries: int = 4,
        backoff_base: float = 0.5,
        backoff_max: float = 30.0,
        timeout: float = 30.0,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url, headers=default_headers or {}, timeout=timeout
        )
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._backoff_max = backoff_max

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        attempt = 0
        while True:
            response = self._client.request(method, url, **kwargs)
            self._log_request(response)
            if response.status_code not in _RETRY_STATUSES or attempt >= self._max_retries:
                response.raise_for_status()
                return response
            delay = self._compute_delay(response, attempt)
            _log.warning(
                "http retry attempt=%d status=%d sleep=%.2fs url=%s",
                attempt + 1,
                response.status_code,
                delay,
                url,
            )
            time.sleep(delay)
            attempt += 1

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def _compute_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
        # Exponential backoff with full jitter, capped.
        exp = self._backoff_base * (2**attempt)
        return min(self._backoff_max, random.uniform(0, exp))

    def _log_request(self, response: httpx.Response) -> None:
        req = response.request
        _log.info(
            "http %s %s -> %d in %.0fms",
            req.method,
            f"{req.url.host}{req.url.path}",
            response.status_code,
            response.elapsed.total_seconds() * 1000,
        )


class _RedactingFilter(logging.Filter):
    """Defense-in-depth: blanks log lines containing sensitive headers.

    Plan-1 deferred-concerns item #2: substrings are narrowed (e.g.
    'token=' not bare 'token') so legitimate log lines mentioning
    things like pagination cursor tokens are not false-positive-redacted.
    """

    _SENSITIVE_SUBSTRINGS = (
        "authorization:",
        "authorization=",
        "bearer ",
        "x-shopify-access-token",
        "x-shopify-storefront-private-token",
        "x-shopify-hmac-sha256",
        "x-api-key",
        "api-key=",
        "token: ",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage().lower()
        for needle in self._SENSITIVE_SUBSTRINGS:
            if needle in msg:
                record.msg = "[redacted sensitive log line]"
                record.args = ()
                return True
        return True


_log.addFilter(_RedactingFilter())
