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

    Note: ``data`` may be ``None`` (Shopify returned only errors) and any nested
    field may itself be ``None``. Callers must guard before drilling into it.
    """

    def __init__(self, message: str, *, data: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.data = data


class ShopifyUserError(RuntimeError):
    """Raised when a Shopify mutation returns a non-empty `userErrors` array.

    Plan-1 deferred-concerns item #16. Distinct from top-level GraphQL `errors`:
    `userErrors` is a per-mutation array with `field` and `message`. The helper
    `ShopifyClient.check_user_errors(payload, *, mutation)` walks the standard
    `data[mutation].userErrors` path and raises if non-empty.
    """

    def __init__(self, mutation: str, errors: list[dict]) -> None:
        self.mutation = mutation
        self.errors = errors
        parts = []
        for e in errors:
            fields = e.get("field") or []
            message = e.get("message", "?")
            if fields:
                parts.append(f"{', '.join(fields)}: {message}")
            else:
                parts.append(message)
        summary = "; ".join(parts)
        super().__init__(f"{mutation} userErrors: {summary}")


class AmbiguousSkuError(RuntimeError):
    """Raised when a SKU lookup returns more than one variant.

    Promoted from products/bulk_prices.py in Plan 3 Batch 1 so other
    scripts (e.g. inventory operations) can reuse the same exception
    type for SKU-resolution failure.
    """

    def __init__(self, sku: str, variant_ids: list[str]) -> None:
        self.sku = sku
        self.variant_ids = variant_ids
        super().__init__(
            f"SKU {sku!r} matched {len(variant_ids)} variants: {', '.join(variant_ids)}. "
            f"Refusing to guess — pass an explicit variant_id instead."
        )


class SkuNotFoundError(LookupError):
    """Raised when a SKU lookup returns zero variants.

    Subclasses LookupError per stdlib convention for 'not found' errors.
    """

    def __init__(self, sku: str) -> None:
        self.sku = sku
        super().__init__(f"SKU {sku!r} not found")


def check_user_errors(data: dict, *, mutation: str) -> None:
    """Raise ShopifyUserError if `data[mutation].userErrors` is non-empty.

    Free function for direct import — preferred for new code:
        from shopify.utils.client import check_user_errors
    The ShopifyClient.check_user_errors staticmethod calls this internally
    and remains as a back-compat shim.
    """
    node = data.get(mutation) or {}
    errs = node.get("userErrors") or []
    if errs:
        raise ShopifyUserError(mutation, errs)


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

    @staticmethod
    def check_user_errors(data: dict, *, mutation: str) -> None:
        """Back-compat shim; delegates to the module-level check_user_errors."""
        check_user_errors(data, mutation=mutation)

    def __enter__(self) -> ShopifyClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()
