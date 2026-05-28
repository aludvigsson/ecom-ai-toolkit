"""Shopify Admin GraphQL client built on core.http.HttpClient."""

from __future__ import annotations

from typing import Any

from core.config import StoreConfig
from core.http import HttpClient
from core.logging import get_logger
from core.secrets import require_secret

_log = get_logger("ecom.shopify.client")


class ShopifyGraphQLError(RuntimeError):
    """Raised when a GraphQL response has a non-empty top-level `errors` array.

    Shopify can return both `data` and `errors` in the same response (partial
    success on list queries, for example). Plan-1 deferred-concerns item #15:
    callers that want to recover from partial failures can read `.data` after
    catching this exception.
    """

    def __init__(self, message: str, *, data: dict | None = None) -> None:
        super().__init__(message)
        self.data = data


class ShopifyClient:
    """Admin GraphQL client.

    Reads SHOPIFY_ADMIN_ACCESS_TOKEN from the environment at construction time.
    """

    def __init__(self, config: StoreConfig) -> None:
        self._config = config
        token = require_secret("SHOPIFY_ADMIN_ACCESS_TOKEN")
        domain = config.store.shopify_domain
        api_version = config.domains["shopify"].api_version or "2025-10"
        self._endpoint = f"https://{domain}/admin/api/{api_version}/graphql.json"
        self._http = HttpClient(
            default_headers={
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    @property
    def shop_domain(self) -> str:
        return self._config.store.shopify_domain

    def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GraphQL operation and return the `data` block."""
        payload = {"query": query, "variables": variables or {}}
        response = self._http.post(self._endpoint, json=payload)
        body = response.json()
        if body.get("errors"):
            raise ShopifyGraphQLError(
                "; ".join(e.get("message", str(e)) for e in body["errors"]),
                data=body.get("data"),
            )
        return body.get("data", {})

    def __enter__(self) -> ShopifyClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()
