"""List Shopify orders with optional date-range, status, and customer filters."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from shopify.utils.cli import add_common_flags, configure_logging_from_args, format_output
from shopify.utils.client import ShopifyClient
from shopify.utils.search import escape_search_value

_QUERY = """
query Orders($first: Int!, $query: String) {
  orders(first: $first, query: $query, sortKey: CREATED_AT, reverse: true) {
    edges {
      node {
        id
        name
        createdAt
        displayFinancialStatus
        displayFulfillmentStatus
        currentTotalPriceSet { shopMoney { amount currencyCode } }
        customer { id email displayName }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


def _build_query(
    date_from: str | None,
    date_to: str | None,
    financial: str | None,
    fulfillment: str | None,
    customer_email: str | None,
) -> str | None:
    parts: list[str] = []
    if date_from:
        parts.append(f"created_at:>={date_from}")
    if date_to:
        parts.append(f"created_at:<={date_to}")
    if financial:
        parts.append(f"financial_status:{financial}")
    if fulfillment:
        parts.append(f"fulfillment_status:{fulfillment}")
    if customer_email:
        parts.append(f"email:{escape_search_value(customer_email)}")
    return " ".join(parts) if parts else None


def _flatten(node: dict) -> dict:
    money = (node.get("currentTotalPriceSet") or {}).get("shopMoney") or {}
    customer = node.get("customer") or {}
    return {
        "id": node.get("id"),
        "name": node.get("name"),
        "createdAt": node.get("createdAt"),
        "displayFinancialStatus": node.get("displayFinancialStatus"),
        "displayFulfillmentStatus": node.get("displayFulfillmentStatus"),
        "total": money.get("amount"),
        "currency": money.get("currencyCode"),
        "customer_email": customer.get("email"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Shopify orders.")
    add_common_flags(parser)
    parser.add_argument("--from", dest="date_from", help="ISO date lower bound (created_at:>=)")
    parser.add_argument("--to", dest="date_to", help="ISO date upper bound (created_at:<=)")
    parser.add_argument("--financial", help="financial_status filter (paid, refunded, ...)")
    parser.add_argument(
        "--fulfillment", help="fulfillment_status filter (fulfilled, unfulfilled, ...)"
    )
    parser.add_argument("--customer-email", dest="customer_email", help="email filter")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    query_str = _build_query(
        args.date_from,
        args.date_to,
        args.financial,
        args.fulfillment,
        args.customer_email,
    )
    variables = {"first": args.limit, "query": query_str}

    with ShopifyClient(config=cfg) as client:
        data = client.graphql(_QUERY, variables)

    rows = [_flatten(edge["node"]) for edge in data["orders"]["edges"]]
    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
