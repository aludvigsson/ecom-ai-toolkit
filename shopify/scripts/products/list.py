"""List Shopify products with optional status/vendor/tag/raw-query filters."""

from __future__ import annotations

import argparse
import sys

from core.config import load_config
from shopify.utils.cli import add_common_flags, format_output
from shopify.utils.client import ShopifyClient

_QUERY = """
query Products($first: Int!, $query: String) {
  products(first: $first, query: $query) {
    edges {
      node {
        id
        title
        handle
        status
        vendor
        totalInventory
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


def _build_query(
    status: str | None,
    vendor: str | None,
    tag: str | None,
    raw: str | None,
) -> str | None:
    parts: list[str] = []
    if status:
        parts.append(f"status:{status.lower()}")
    if vendor:
        parts.append(f"vendor:'{vendor}'")
    if tag:
        parts.append(f"tag:'{tag}'")
    if raw:
        parts.append(raw)
    return " ".join(parts) if parts else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Shopify products.")
    add_common_flags(parser)
    parser.add_argument("--status", choices=("ACTIVE", "DRAFT", "ARCHIVED"))
    parser.add_argument("--vendor")
    parser.add_argument("--tag")
    parser.add_argument("--query", help="Raw Shopify product query string")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    query_str = _build_query(args.status, args.vendor, args.tag, args.query)
    variables = {"first": args.limit, "query": query_str}

    with ShopifyClient(config=cfg) as client:
        data = client.graphql(_QUERY, variables)

    rows = [edge["node"] for edge in data["products"]["edges"]]
    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
