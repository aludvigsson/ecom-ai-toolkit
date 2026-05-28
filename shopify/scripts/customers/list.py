"""List Shopify customers with optional email, tag, state, and min-orders filters."""

from __future__ import annotations

import argparse
import sys

from core.config import load_config
from shopify.utils.cli import add_common_flags, format_output
from shopify.utils.client import ShopifyClient
from shopify.utils.search import escape_search_value

_QUERY = """
query Customers($first: Int!, $query: String) {
  customers(first: $first, query: $query, sortKey: UPDATED_AT, reverse: true) {
    edges {
      node {
        id
        email
        displayName
        createdAt
        updatedAt
        numberOfOrders
        amountSpent { amount currencyCode }
        tags
        state
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

_STATE_CHOICES = ("enabled", "disabled", "invited", "declined")


def _build_query(
    email: str | None,
    tag: str | None,
    state: str | None,
) -> str | None:
    parts: list[str] = []
    if email:
        parts.append(f"email:{escape_search_value(email)}")
    if tag:
        parts.append(f"tag:'{escape_search_value(tag)}'")
    if state:
        parts.append(f"state:{state}")
    return " ".join(parts) if parts else None


def _flatten(node: dict, output_fmt: str) -> dict:
    money = node.get("amountSpent") or {}
    tags = node.get("tags") or []
    return {
        "id": node.get("id"),
        "email": node.get("email"),
        "displayName": node.get("displayName"),
        "numberOfOrders": node.get("numberOfOrders"),
        "total_spent": money.get("amount"),
        "currency": money.get("currencyCode"),
        "tags": ", ".join(tags) if output_fmt != "json" else tags,
        "state": node.get("state"),
        "updatedAt": node.get("updatedAt"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Shopify customers.")
    add_common_flags(parser)
    parser.add_argument("--email", help="Filter by email (composes email:<value>)")
    parser.add_argument("--tag", help="Filter by tag (composes tag:'<value>')")
    parser.add_argument(
        "--state",
        choices=_STATE_CHOICES,
        help="Filter by customer account state",
    )
    parser.add_argument(
        "--min-orders",
        dest="min_orders",
        type=int,
        help="Post-filter: minimum numberOfOrders (applied in memory)",
    )
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    query_str = _build_query(args.email, args.tag, args.state)
    variables = {"first": args.limit, "query": query_str}

    with ShopifyClient(config=cfg) as client:
        data = client.graphql(_QUERY, variables)

    rows = [_flatten(edge["node"], args.output) for edge in data["customers"]["edges"]]
    if args.min_orders is not None:
        rows = [r for r in rows if (r.get("numberOfOrders") or 0) >= args.min_orders]
    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
