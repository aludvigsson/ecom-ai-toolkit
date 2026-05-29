"""Meta (Facebook/Instagram) Marketing Graph API client on core.http.HttpClient.

Mirrors klaviyo.utils.client.KlaviyoClient in shape (reads its secret at
construction, thin verb wrappers over core.http.HttpClient which retries
429/5xx, context manager) but speaks the Graph API: a versioned base URL,
``Authorization: Bearer <token>`` auth, ``act_<id>`` account-id normalization,
``paging.next``-following pagination, and ``check_error`` surfacing the Graph
``error{message,code,error_subcode,fbtrace_id}`` object.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from core.config import StoreConfig
from core.http import HttpClient
from core.logging import get_logger
from core.secrets import require_secret

_log = get_logger("ecom.meta_ads.client")

# Known-good Graph API version used when domains.meta_ads.api_version is unset.
# Override per-invocation with --api-version (see meta_ads.utils.cli.add_meta_flags).
_DEFAULT_VERSION = "v21.0"

# Graph error codes that mean the access token is bad/expired.
_TOKEN_ERROR_CODES = {102, 190}


class MetaAPIError(RuntimeError):
    """Raised when a Graph response carries a top-level ``error`` object.

    Surfaces ``message``, ``code``, ``error_subcode``, and ``fbtrace_id`` (the
    last is essential when escalating to Meta support). Token errors (code
    102/190) additionally name the ``META_ACCESS_TOKEN`` env var.
    """

    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        subcode: int | None = None,
        fbtrace_id: str | None = None,
        body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.subcode = subcode
        self.fbtrace_id = fbtrace_id
        self.body = body


def account_path(account_id: str | int) -> str:
    """Normalize an ad-account id to the Graph ``act_<id>`` node form.

    Accepts a bare id (``"123"``/``123``) or an already-prefixed ``"act_123"``.
    """
    text = str(account_id)
    return text if text.startswith("act_") else f"act_{text}"


def check_error(body: dict[str, Any] | None) -> None:
    """Raise MetaAPIError if ``body['error']`` is present.

    Free function for direct import:
        from meta_ads.utils.client import check_error
    """
    if not body:
        return
    error = body.get("error")
    if not error:
        return
    message = error.get("message") or "?"
    code = error.get("code")
    subcode = error.get("error_subcode")
    fbtrace_id = error.get("fbtrace_id")
    parts = [message]
    if code is not None:
        parts.append(f"code={code}")
    if subcode is not None:
        parts.append(f"subcode={subcode}")
    if fbtrace_id:
        parts.append(f"fbtrace_id={fbtrace_id}")
    if code in _TOKEN_ERROR_CODES:
        parts.append("(check META_ACCESS_TOKEN)")
    raise MetaAPIError(
        " ".join(parts),
        code=code,
        subcode=subcode,
        fbtrace_id=fbtrace_id,
        body=body,
    )


class MetaClient:
    """Meta Marketing Graph API client.

    Reads META_ACCESS_TOKEN from the environment at construction time. The Graph
    API version segment of the base URL comes from
    config.domains['meta_ads'].api_version, falling back to _DEFAULT_VERSION,
    overridable via the ``api_version`` argument.
    """

    def __init__(self, config: StoreConfig, *, api_version: str | None = None) -> None:
        self._config = config
        token = require_secret("META_ACCESS_TOKEN")
        domain = config.domains.get("meta_ads")
        configured = domain.api_version if domain else None
        self._version = api_version or configured or _DEFAULT_VERSION
        self._http = HttpClient(
            base_url=f"https://graph.facebook.com/{self._version}/",
            default_headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )

    @property
    def api_version(self) -> str:
        return self._version

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._http.get(path, params=params)
        return response.json()

    def post(self, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """POST form-encoded data (Graph creates/updates are form POSTs)."""
        response = self._http.post(path, data=data)
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def delete(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._http.delete(path, params=params)
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
        """Yield ``data[]`` items across pages by following ``paging.next``.

        The Graph API returns a fully-qualified ``paging.next`` URL (carrying the
        cursor), so subsequent requests pass it through unchanged. When ``limit``
        is set, stops after yielding that many items (logs a truncation notice).
        """
        next_url: str | None = path
        first = True
        yielded = 0
        while next_url:
            body = self.get(next_url, params=params if first else None)
            first = False
            check_error(body)
            for item in body.get("data") or []:
                if limit is not None and yielded >= limit:
                    _log.info("paginate truncated at limit=%d for %s", limit, path)
                    return
                yield item
                yielded += 1
            next_url = (body.get("paging") or {}).get("next")

    def __enter__(self) -> MetaClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()
