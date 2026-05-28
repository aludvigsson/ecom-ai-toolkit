"""Topic → handler dispatch. Each handler accepts a parsed JSON payload."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from shopify.scripts.webhooks.receiver.handlers import (
    app_uninstalled,
    orders_create,
    orders_updated,
    products_update,
)

HANDLERS: dict[str, Callable[[dict[str, Any]], None]] = {
    "orders/create": orders_create.handle,
    "orders/updated": orders_updated.handle,
    "products/update": products_update.handle,
    "app/uninstalled": app_uninstalled.handle,
}
