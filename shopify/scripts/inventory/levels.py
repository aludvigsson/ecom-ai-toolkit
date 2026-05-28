"""Read per-SKU inventory levels across all locations.

For each SKU passed via repeatable ``--sku`` or via a ``--from-csv`` file
(with a ``sku`` column), looks up the variant and emits one row per
(sku, location) flattened. The ``quantities`` array
(``available`` / ``on_hand`` / ``committed`` / ``reserved``) is
denormalised to columns; missing names default to 0.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.config import load_config
from shopify.utils.cli import add_common_flags, format_output
from shopify.utils.client import (
    AmbiguousSkuError,
    ShopifyClient,
    SkuNotFoundError,
)
from shopify.utils.csv_io import read_csv_dicts
from shopify.utils.search import escape_search_value

_QUERY = """
query VariantBySku($q: String!) {
  productVariants(first: 2, query: $q) {
    edges { node {
      id sku
      inventoryItem {
        id tracked
        inventoryLevels(first: 50) {
          edges { node {
            quantities(names: ["available", "on_hand", "committed", "reserved"]) { name quantity }
            location { id name }
          } }
        }
      }
    } }
  }
}
"""

_QUANTITY_NAMES = ("available", "on_hand", "committed", "reserved")


def _read_skus_from_csv(path: Path) -> list[str]:
    skus: list[str] = []
    for row in read_csv_dicts(path):
        sku = (row.get("sku") or "").strip()
        if sku:
            skus.append(sku)
    return skus


def _quantities_by_name(quantities: list[dict]) -> dict[str, int]:
    return {q["name"]: q.get("quantity", 0) for q in quantities or []}


def _rows_for_variant(sku: str, variant_node: dict) -> list[dict]:
    inventory_item = variant_node.get("inventoryItem") or {}
    tracked = inventory_item.get("tracked")
    level_edges = (inventory_item.get("inventoryLevels") or {}).get("edges") or []
    rows: list[dict] = []
    for edge in level_edges:
        node = edge["node"]
        loc = node.get("location") or {}
        qmap = _quantities_by_name(node.get("quantities") or [])
        rows.append(
            {
                "sku": sku,
                "variant_id": variant_node.get("id"),
                "tracked": tracked,
                "location_id": loc.get("id"),
                "location_name": loc.get("name"),
                "available": qmap.get("available", 0),
                "on_hand": qmap.get("on_hand", 0),
                "committed": qmap.get("committed", 0),
                "reserved": qmap.get("reserved", 0),
            }
        )
    return rows


def _fetch_variant(client: ShopifyClient, sku: str) -> dict:
    data = client.graphql(_QUERY, {"q": f"sku:'{escape_search_value(sku)}'"})
    edges = (data.get("productVariants") or {}).get("edges") or []
    if not edges:
        raise SkuNotFoundError(sku)
    if len(edges) > 1:
        raise AmbiguousSkuError(sku, [e["node"]["id"] for e in edges])
    return edges[0]["node"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read per-SKU inventory levels across all locations."
    )
    add_common_flags(parser)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--sku",
        action="append",
        help="SKU to look up. Repeat for multiple SKUs.",
    )
    source.add_argument(
        "--from-csv",
        dest="from_csv",
        help="Path to CSV with a 'sku' column",
    )
    args = parser.parse_args(argv)

    skus = _read_skus_from_csv(Path(args.from_csv)) if args.from_csv else list(args.sku or [])

    cfg = load_config(args.config)
    rows: list[dict] = []
    with ShopifyClient(config=cfg) as client:
        for sku in skus:
            node = _fetch_variant(client, sku)
            rows.extend(_rows_for_variant(sku, node))

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
