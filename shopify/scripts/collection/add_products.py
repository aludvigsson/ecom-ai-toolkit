"""Bulk add products to a Shopify collection.

Input modes are mutually exclusive: --from-csv (with a product_id or handle
column) or --handles (comma-separated). Handles are resolved to GIDs via
productByHandle. Mutations are chunked at 250 product IDs per call.
Honors --dry-run by printing each chunk and exiting 0.
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
from shopify.utils.client import ShopifyClient, check_user_errors
from shopify.utils.csv_io import read_csv_dicts

_CHUNK_SIZE = 250

_LOOKUP_BY_HANDLE = """
query ProductIdByHandle($handle: String!) {
  productByHandle(handle: $handle) { id }
}
"""

_MUTATION = """
mutation CollectionAddProducts($id: ID!, $productIds: [ID!]!) {
  collectionAddProducts(id: $id, productIds: $productIds) {
    collection { id }
    userErrors { field message }
  }
}
"""


def _items_from_csv(path: str) -> list[tuple[str, str]]:
    """Return list of (kind, value) tuples where kind is 'id' or 'handle'."""
    items: list[tuple[str, str]] = []
    for row in read_csv_dicts(path):
        pid = (row.get("product_id") or "").strip()
        if pid:
            items.append(("id", pid))
            continue
        handle = (row.get("handle") or "").strip()
        if handle:
            items.append(("handle", handle))
    return items


def _items_from_handles(handle_csv: str) -> list[tuple[str, str]]:
    return [("handle", h.strip()) for h in handle_csv.split(",") if h.strip()]


def _resolve(items: list[tuple[str, str]], client: ShopifyClient) -> list[str]:
    return [value if kind == "id" else _resolve_handle(value, client) for kind, value in items]


def _resolve_handle(handle: str, client: ShopifyClient) -> str:
    data = client.graphql(_LOOKUP_BY_HANDLE, {"handle": handle})
    node = data.get("productByHandle")
    if not node or not node.get("id"):
        raise RuntimeError(f"No product found for handle: {handle}")
    return node["id"]


def _chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bulk add products to a Shopify collection.",
    )
    add_common_flags(parser)
    parser.add_argument("--collection-id", required=True, help="Collection GID")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--from-csv", help="CSV with product_id or handle column")
    source.add_argument("--handles", help="Comma-separated product handles")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)

    items = _items_from_csv(args.from_csv) if args.from_csv else _items_from_handles(args.handles)

    if args.dry_run:
        raw_values = [v for _, v in items]
        chunks = _chunked(raw_values, _CHUNK_SIZE)
        print(
            format_output(
                [{"chunk": i, "productIds": c} for i, c in enumerate(chunks)],
                args.output,
            )
        )
        return 0

    with ShopifyClient(config=cfg) as client:
        product_ids = _resolve(items, client)
        chunks = _chunked(product_ids, _CHUNK_SIZE)
        results = []
        for chunk in chunks:
            data = client.graphql(
                _MUTATION,
                {"id": args.collection_id, "productIds": chunk},
            )
            check_user_errors(data, mutation="collectionAddProducts")
            results.append(data["collectionAddProducts"]["collection"])

    print(format_output(results, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
