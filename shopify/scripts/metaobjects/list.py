"""List Shopify metaobjects of a given type.

Table output collapses the raw ``fields`` array to a ``fields_count`` column
for readability; JSON output keeps the full field list.
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
from shopify.utils.client import ShopifyClient

_QUERY = """
query Metaobjects($type: String!, $first: Int!) {
  metaobjects(type: $type, first: $first) {
    edges {
      node {
        id handle type displayName updatedAt
        fields { key value type }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Shopify metaobjects of a given type.")
    add_common_flags(parser)
    parser.add_argument("--type", required=True, help="Metaobject type")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    variables = {"type": args.type, "first": args.limit}

    with ShopifyClient(config=cfg) as client:
        data = client.graphql(_QUERY, variables)

    rows = [edge["node"] for edge in data["metaobjects"]["edges"]]
    for r in rows:
        fields = r.get("fields", [])
        r["fields_count"] = len(fields) if isinstance(fields, list) else 0
        if args.output == "table":
            r.pop("fields", None)

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
