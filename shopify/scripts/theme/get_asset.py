"""Read a single OS 2.0 theme file.

Default `--output text` prints just the body content (so the script is
pipe-friendly: `... > local.json`). `--output json` prints the full file
node. Exits 2 when the file is not present in the theme.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import json
import sys

from core.config import load_config
from shopify.utils.cli import add_common_flags, configure_logging_from_args
from shopify.utils.client import ShopifyClient

_QUERY = """
query Asset($themeId: ID!, $filenames: [String!]!) {
  theme(id: $themeId) {
    files(filenames: $filenames, first: 1) {
      edges {
        node {
          filename
          body {
            ... on OnlineStoreThemeFileBodyText { content }
          }
          size
          contentType
        }
      }
    }
  }
}
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read a Shopify theme file.")
    add_common_flags(parser)
    # Override --output: this script outputs raw file content by default
    # (text) so it pipes cleanly into local files. JSON returns the node.
    for action in parser._actions:
        if action.dest == "output":
            action.choices = ("text", "json")
            action.default = "text"
            break
    parser.add_argument("--theme-id", required=True, help="Theme GID")
    parser.add_argument(
        "--filename",
        required=True,
        help="Theme file path, e.g. templates/product.json",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    variables = {"themeId": args.theme_id, "filenames": [args.filename]}

    with ShopifyClient(config=cfg) as client:
        data = client.graphql(_QUERY, variables)

    theme = data.get("theme") or {}
    edges = (theme.get("files") or {}).get("edges") or []
    if not edges:
        print(
            f"File not found in theme: {args.filename}",
            file=sys.stderr,
        )
        return 2

    node = edges[0]["node"]
    if args.output == "json":
        print(json.dumps(node, indent=2, default=str))
    else:
        body = node.get("body") or {}
        print(body.get("content", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
