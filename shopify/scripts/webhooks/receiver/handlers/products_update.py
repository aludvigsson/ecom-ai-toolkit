"""products/update — stub. Fill in business logic for your store."""

from __future__ import annotations

from typing import Any

from core.logging import get_logger

_log = get_logger("ecom.webhooks.products_update")


def handle(payload: dict[str, Any]) -> None:
    _log.info("products/update received id=%s title=%s", payload.get("id"), payload.get("title"))
    # TODO: wire to your domain logic (e.g. re-sync feed, bust cache, reindex search, etc.)
