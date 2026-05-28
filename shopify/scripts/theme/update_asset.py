"""Update (upsert) a single OS 2.0 theme file.

Destructive: requires ``--yes`` to actually run the mutation. Always
fetches the current content first, computes a unified diff via
``shopify.utils.diff.make_diff``, and prints the diff to STDERR so
stdout stays clean for piping. ``--dry-run`` prints the diff and
exits 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from shopify.utils.cli import add_common_flags, configure_logging_from_args
from shopify.utils.client import ShopifyClient, check_user_errors
from shopify.utils.diff import make_diff

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
        }
      }
    }
  }
}
"""

_MUTATION = """
mutation Upsert($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
  themeFilesUpsert(themeId: $themeId, files: $files) {
    upsertedThemeFiles { filename }
    userErrors { field message code }
  }
}
"""


def _resolve_new_content(args: argparse.Namespace) -> str:
    if args.from_file:
        with open(args.from_file, encoding="utf-8") as fh:
            return fh.read()
    if args.content is not None:
        return args.content
    # --content-stdin
    return sys.stdin.read()


def _fetch_current_content(client: ShopifyClient, theme_id: str, filename: str) -> str:
    data = client.graphql(_QUERY, {"themeId": theme_id, "filenames": [filename]})
    theme = data.get("theme") or {}
    edges = (theme.get("files") or {}).get("edges") or []
    if not edges:
        return ""
    body = edges[0]["node"].get("body") or {}
    return body.get("content", "") or ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update a Shopify theme file (upsert).")
    add_common_flags(parser)
    parser.add_argument("--theme-id", required=True, help="Theme GID")
    parser.add_argument(
        "--filename",
        required=True,
        help="Theme file path, e.g. templates/product.json",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--from-file", help="Read new content from a local file")
    source.add_argument("--content", help="Inline new content as a string")
    source.add_argument(
        "--content-stdin",
        action="store_true",
        help="Read new content from stdin",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm destructive write (required for live execution)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if args.dry_run and args.yes:
        print("note: --dry-run takes precedence over --yes", file=sys.stderr)

    new_content = _resolve_new_content(args)

    cfg = load_config(args.config)
    with ShopifyClient(config=cfg) as client:
        old_content = _fetch_current_content(client, args.theme_id, args.filename)
        diff = make_diff(old_content, new_content, path=args.filename)
        # Print diff to STDERR so stdout stays clean for piping.
        if diff:
            print(diff, file=sys.stderr)
        else:
            print("(no changes)", file=sys.stderr)

        if args.dry_run:
            return 0

        if not args.yes:
            print("Use --yes to apply the change", file=sys.stderr)
            return 1

        files_input = [
            {
                "filename": args.filename,
                "body": {"type": "TEXT", "value": new_content},
            }
        ]
        data = client.graphql(
            _MUTATION,
            {"themeId": args.theme_id, "files": files_input},
        )

    check_user_errors(data, mutation="themeFilesUpsert")
    print(f"Updated: {args.filename}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
