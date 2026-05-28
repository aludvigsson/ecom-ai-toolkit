"""List Shopify discounts (code and/or automatic).

Shopify exposes two parallel discount catalogs:

- ``codeDiscountNodes`` — discounts that require a coupon code entered at
  checkout.
- ``automaticDiscountNodes`` — discounts that apply automatically based on
  rules in the cart.

This script queries one or both based on ``--type`` and flattens the
``__typename`` into a ``kind`` column. For code discounts the first code
from the ``codes`` connection is surfaced as the ``code`` column;
automatic discounts have ``code = None``.

``--status`` is applied client-side (Shopify's discount-node connections
don't accept it as a query argument).
"""

from __future__ import annotations

import argparse
import sys

from core.config import load_config
from shopify.utils.cli import add_common_flags, format_output
from shopify.utils.client import ShopifyClient

_CODE_QUERY = """
query CodeDiscounts($first: Int!) {
  codeDiscountNodes(first: $first) {
    edges {
      node {
        id
        codeDiscount {
          __typename
          ... on DiscountCodeBasic {
            title summary status startsAt endsAt
            codes(first: 1) { edges { node { code } } }
          }
          ... on DiscountCodeBxgy {
            title summary status startsAt endsAt
            codes(first: 1) { edges { node { code } } }
          }
          ... on DiscountCodeFreeShipping {
            title summary status startsAt endsAt
            codes(first: 1) { edges { node { code } } }
          }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

_AUTOMATIC_QUERY = """
query AutomaticDiscounts($first: Int!) {
  automaticDiscountNodes(first: $first) {
    edges {
      node {
        id
        automaticDiscount {
          __typename
          ... on DiscountAutomaticBasic { title summary status startsAt endsAt }
          ... on DiscountAutomaticBxgy { title summary status startsAt endsAt }
          ... on DiscountAutomaticFreeShipping { title summary status startsAt endsAt }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


def _flatten_code_node(node: dict) -> dict:
    disc = node.get("codeDiscount") or {}
    codes_conn = disc.get("codes") or {}
    code_edges = codes_conn.get("edges") or []
    code = (code_edges[0]["node"]["code"]) if code_edges else None
    return {
        "id": node.get("id"),
        "kind": disc.get("__typename"),
        "title": disc.get("title"),
        "summary": disc.get("summary"),
        "status": disc.get("status"),
        "startsAt": disc.get("startsAt"),
        "endsAt": disc.get("endsAt"),
        "code": code,
    }


def _flatten_automatic_node(node: dict) -> dict:
    disc = node.get("automaticDiscount") or {}
    return {
        "id": node.get("id"),
        "kind": disc.get("__typename"),
        "title": disc.get("title"),
        "summary": disc.get("summary"),
        "status": disc.get("status"),
        "startsAt": disc.get("startsAt"),
        "endsAt": disc.get("endsAt"),
        "code": None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Shopify discounts.")
    add_common_flags(parser)
    parser.add_argument(
        "--type",
        choices=("code", "automatic", "all"),
        default="all",
        help="Which catalog to query",
    )
    parser.add_argument(
        "--status",
        choices=("ACTIVE", "EXPIRED", "SCHEDULED"),
        help="Post-filter on discount status (client-side)",
    )
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    rows: list[dict] = []

    with ShopifyClient(config=cfg) as client:
        if args.type in ("code", "all"):
            data = client.graphql(_CODE_QUERY, {"first": args.limit})
            for edge in data["codeDiscountNodes"]["edges"]:
                rows.append(_flatten_code_node(edge["node"]))
        if args.type in ("automatic", "all"):
            data = client.graphql(_AUTOMATIC_QUERY, {"first": args.limit})
            for edge in data["automaticDiscountNodes"]["edges"]:
                rows.append(_flatten_automatic_node(edge["node"]))

    if args.status:
        rows = [r for r in rows if r.get("status") == args.status]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
