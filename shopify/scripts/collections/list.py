"""List Shopify collections with optional type and raw-query filters."""

from __future__ import annotations

import argparse
import sys

from core.config import load_config
from shopify.utils.cli import add_common_flags, configure_logging_from_args, format_output
from shopify.utils.client import ShopifyClient

_QUERY = """
query Collections($first: Int!, $query: String) {
  collections(first: $first, query: $query) {
    edges {
      node {
        id
        title
        handle
        productsCount { count }
        sortOrder
        updatedAt
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


def _build_query(collection_type: str, raw: str | None) -> str | None:
    parts: list[str] = []
    if collection_type in ("smart", "custom"):
        parts.append(f"collection_type:{collection_type}")
    if raw:
        parts.append(raw)
    return " ".join(parts) if parts else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Shopify collections.")
    add_common_flags(parser)
    parser.add_argument(
        "--type",
        choices=("smart", "custom", "all"),
        default="all",
        help="Filter by collection type",
    )
    parser.add_argument("--query", help="Raw Shopify collection query string")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    query_str = _build_query(args.type, args.query)
    variables = {"first": args.limit, "query": query_str}

    with ShopifyClient(config=cfg) as client:
        data = client.graphql(_QUERY, variables)

    rows = [edge["node"] for edge in data["collections"]["edges"]]
    for r in rows:
        pc = r.get("productsCount")
        if isinstance(pc, dict):
            r["productsCount"] = pc.get("count", 0)
    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
