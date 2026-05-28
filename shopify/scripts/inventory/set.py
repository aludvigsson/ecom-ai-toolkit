"""Set the on-hand inventory quantity for a SKU at a specific location.

Two-step resolution:

1. ``--sku`` → ``inventoryItem.id`` via ``productVariants(first: 2, query:"sku:'<escaped>'")``.
   Reuses the shared ``AmbiguousSkuError`` / ``SkuNotFoundError`` guards.
2. ``--location-id`` OR ``--location-name`` (mutually exclusive). When resolving
   by name, a case-insensitive exact match is required; 0 matches raises
   ``LocationNotFoundError``, >1 raises ``AmbiguousLocationError``.

Then calls ``inventorySetOnHandQuantities``. Honors ``--dry-run`` by printing
the resolved payload and exiting 0 without calling the mutation.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from shopify.utils.cli import add_common_flags, configure_logging_from_args, format_output
from shopify.utils.client import (
    AmbiguousSkuError,
    ShopifyClient,
    SkuNotFoundError,
    check_user_errors,
)
from shopify.utils.search import escape_search_value

_SKU_LOOKUP = """
query VariantBySku($q: String!) {
  productVariants(first: 2, query: $q) {
    edges { node { id sku inventoryItem { id } } }
  }
}
"""

_LOCATIONS_QUERY = """
query Locations {
  locations(first: 50) {
    edges { node { id name } }
  }
}
"""

_MUTATION = """
mutation Set($input: InventorySetOnHandQuantitiesInput!) {
  inventorySetOnHandQuantities(input: $input) {
    inventoryAdjustmentGroup { id reason changes { name delta quantityAfterChange } }
    userErrors { field message code }
  }
}
"""


class LocationNotFoundError(LookupError):
    """Raised when ``--location-name`` matches zero locations."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Location {name!r} not found")


class AmbiguousLocationError(RuntimeError):
    """Raised when ``--location-name`` matches more than one location."""

    def __init__(self, name: str, location_ids: list[str]) -> None:
        self.name = name
        self.location_ids = location_ids
        super().__init__(
            f"Location name {name!r} matched {len(location_ids)} locations: "
            f"{', '.join(location_ids)}. Pass --location-id instead."
        )


def _resolve_inventory_item(client: ShopifyClient, sku: str) -> str:
    data = client.graphql(_SKU_LOOKUP, {"q": f"sku:'{escape_search_value(sku)}'"})
    edges = (data.get("productVariants") or {}).get("edges") or []
    if not edges:
        raise SkuNotFoundError(sku)
    if len(edges) > 1:
        raise AmbiguousSkuError(sku, [e["node"]["id"] for e in edges])
    inv = (edges[0]["node"].get("inventoryItem") or {}).get("id")
    if not inv:
        raise SkuNotFoundError(sku)
    return inv


def _resolve_location_by_name(client: ShopifyClient, name: str) -> str:
    data = client.graphql(_LOCATIONS_QUERY)
    edges = (data.get("locations") or {}).get("edges") or []
    target = name.lower()
    matches = [e["node"] for e in edges if (e["node"].get("name") or "").lower() == target]
    if not matches:
        raise LocationNotFoundError(name)
    if len(matches) > 1:
        raise AmbiguousLocationError(name, [m["id"] for m in matches])
    return matches[0]["id"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Set on-hand inventory quantity for a SKU at a location."
    )
    add_common_flags(parser)
    parser.add_argument("--sku", required=True, help="SKU to adjust")
    loc = parser.add_mutually_exclusive_group(required=True)
    loc.add_argument("--location-id", dest="location_id", help="Location GID")
    loc.add_argument(
        "--location-name",
        dest="location_name",
        help="Location name (case-insensitive exact match)",
    )
    parser.add_argument("--quantity", required=True, type=int, help="On-hand quantity to set")
    parser.add_argument(
        "--reason",
        default="correction",
        help=(
            "InventoryAdjustmentReasonInput value. Common: correction, "
            "cycle_count_available, damaged, movement_created, movement_updated, "
            "movement_received, movement_canceled, other, promotion, "
            "quality_control, received, reservation_created, reservation_deleted, "
            "reservation_updated, restock, safety_stock, shrinkage."
        ),
    )
    parser.add_argument(
        "--reference-uri",
        dest="reference_uri",
        default="internal://manual",
        help="referenceDocumentUri for the adjustment group",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)

    with ShopifyClient(config=cfg) as client:
        inventory_item_id = _resolve_inventory_item(client, args.sku)
        location_id = (
            args.location_id
            if args.location_id
            else _resolve_location_by_name(client, args.location_name)
        )

        mutation_input = {
            "reason": args.reason,
            "referenceDocumentUri": args.reference_uri,
            "setQuantities": [
                {
                    "inventoryItemId": inventory_item_id,
                    "locationId": location_id,
                    "quantity": args.quantity,
                }
            ],
        }

        if args.dry_run:
            print(format_output(mutation_input, args.output))
            return 0

        data = client.graphql(_MUTATION, {"input": mutation_input})

    check_user_errors(data, mutation="inventorySetOnHandQuantities")
    group = data["inventorySetOnHandQuantities"]["inventoryAdjustmentGroup"] or {}
    changes = group.get("changes") or []
    print(format_output(changes, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
