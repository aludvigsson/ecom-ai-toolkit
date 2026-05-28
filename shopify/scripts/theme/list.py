"""List Shopify online-store themes with optional role filter.

The `themes` connection doesn't accept role as a query arg, so `--role`
is applied in-memory after the fetch.
"""

from __future__ import annotations

import argparse
import sys

from core.config import load_config
from shopify.utils.cli import add_common_flags, configure_logging_from_args, format_output
from shopify.utils.client import ShopifyClient

_QUERY = """
query Themes($first: Int!) {
  themes(first: $first) {
    edges {
      node {
        id
        name
        role
        processing
        previewable
        updatedAt
      }
    }
  }
}
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Shopify online-store themes.")
    add_common_flags(parser)
    parser.add_argument(
        "--role",
        choices=("MAIN", "UNPUBLISHED", "DEMO", "DEVELOPMENT"),
        help="Filter themes by role (in-memory post-filter)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    variables = {"first": args.limit}

    with ShopifyClient(config=cfg) as client:
        data = client.graphql(_QUERY, variables)

    rows = [edge["node"] for edge in data["themes"]["edges"]]
    if args.role:
        rows = [r for r in rows if r.get("role") == args.role]
    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
