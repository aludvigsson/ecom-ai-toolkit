"""orders/create — stub. Fill in business logic for your store."""

from __future__ import annotations

from typing import Any

from core.logging import get_logger

_log = get_logger("ecom.webhooks.orders_create")


def handle(payload: dict[str, Any]) -> None:
    _log.info("orders/create received id=%s name=%s", payload.get("id"), payload.get("name"))
    # TODO: wire to your domain logic (e.g. enqueue follow-up, mirror to warehouse, etc.)
    # Keep it fast (Shopify retries after ~5s) and idempotent (key on payload id);
    # offload slow work to a background task/queue. See the shopify-webhooks skill.
