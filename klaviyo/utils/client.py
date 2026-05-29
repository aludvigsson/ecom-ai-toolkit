"""Klaviyo JSON:API client built on core.http.HttpClient.

Mirrors shopify.utils.client.ShopifyClient: reads its secret at construction,
sends domain auth + the dated ``revision`` header, exposes thin verb wrappers
over core.http.HttpClient (which retries 429/5xx), and is a context manager.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from core.config import StoreConfig
from core.http import HttpClient
from core.logging import get_logger
from core.secrets import require_secret

_log = get_logger("ecom.klaviyo.client")

_BASE_URL = "https://a.klaviyo.com/api/"

# Known-good dated revision used when domains.klaviyo.api_version is unset.
# Override per-invocation with --revision (see klaviyo.utils.cli.add_klaviyo_flags).
_DEFAULT_REVISION = "2024-10-15"


class KlaviyoAPIError(RuntimeError):
    """Raised when a JSON:API response carries a non-empty top-level ``errors`` array.

    Carries the raw ``errors`` list and the optional parsed ``body`` so callers
    can inspect partial results. Analogous to Shopify's user-error handling.
    """

    def __init__(
        self,
        message: str,
        *,
        errors: list[dict] | None = None,
        body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.errors = errors or []
        self.body = body


class ResourceNotFoundError(LookupError):
    """Raised when a lookup (e.g. profile by email) returns zero results.

    Subclasses LookupError per stdlib convention, mirroring Shopify's
    SkuNotFoundError.
    """

    def __init__(self, what: str) -> None:
        self.what = what
        super().__init__(f"{what} not found")


def check_errors(body: dict[str, Any] | None) -> None:
    """Raise KlaviyoAPIError if ``body['errors']`` is a non-empty list.

    Summarizes each error's ``detail`` and, when present, its
    ``source.pointer``. Free function for direct import:
        from klaviyo.utils.client import check_errors
    """
    if not body:
        return
    errors = body.get("errors") or []
    if not errors:
        return
    parts = []
    for err in errors:
        detail = err.get("detail") or err.get("title") or "?"
        pointer = (err.get("source") or {}).get("pointer")
        parts.append(f"{detail} ({pointer})" if pointer else detail)
    raise KlaviyoAPIError("; ".join(parts), errors=errors, body=body)


class KlaviyoClient:
    """Klaviyo JSON:API client.

    Reads KLAVIYO_PRIVATE_API_KEY from the environment at construction time.
    The dated ``revision`` header comes from config.domains['klaviyo'].api_version,
    falling back to _DEFAULT_REVISION, overridable via the ``revision`` argument.
    """

    def __init__(self, config: StoreConfig, *, revision: str | None = None) -> None:
        self._config = config
        key = require_secret("KLAVIYO_PRIVATE_API_KEY")
        domain = config.domains.get("klaviyo")
        configured = domain.api_version if domain else None
        self._revision = revision or configured or _DEFAULT_REVISION
        self._http = HttpClient(
            base_url=_BASE_URL,
            default_headers={
                "Authorization": f"Klaviyo-API-Key {key}",
                "revision": self._revision,
                "accept": "application/vnd.api+json",
                "content-type": "application/vnd.api+json",
            },
        )

    @property
    def revision(self) -> str:
        return self._revision

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._http.get(path, params=params)
        return response.json()

    def post(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._http.post(path, json=json)
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def patch(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._http.patch(path, json=json)
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def delete(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._http.delete(path, json=json) if json else self._http.delete(path)
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def paginate(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        limit: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield ``data[]`` items across pages by following ``links.next``.

        Klaviyo uses cursor pagination; ``links.next`` is a fully-qualified URL,
        so subsequent requests pass it through unchanged. When ``limit`` is set,
        stops after yielding that many items (logs a truncation notice).
        """
        next_url: str | None = path
        first = True
        yielded = 0
        while next_url:
            body = self.get(next_url, params=params if first else None)
            first = False
            check_errors(body)
            for item in body.get("data") or []:
                if limit is not None and yielded >= limit:
                    _log.info("paginate truncated at limit=%d for %s", limit, path)
                    return
                yield item
                yielded += 1
            next_url = (body.get("links") or {}).get("next")

    def __enter__(self) -> KlaviyoClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()
