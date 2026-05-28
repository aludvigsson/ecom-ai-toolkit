"""app/uninstalled — stub. Fill in business logic for your store."""

from __future__ import annotations

from typing import Any

from core.logging import get_logger

_log = get_logger("ecom.webhooks.app_uninstalled")


def handle(payload: dict[str, Any]) -> None:
    _log.info("app/uninstalled received domain=%s", payload.get("domain"))
    # TODO: wire to your domain logic (e.g. revoke tokens, purge stored shop data, etc.)
