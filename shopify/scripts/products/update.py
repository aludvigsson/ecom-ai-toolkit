"""Update a Shopify product.

Builds ProductInput from non-None CLI flags so we don't blank fields we
didn't ask to update. Honors --dry-run by printing the would-be input
and exiting 0 without calling the mutation.
"""

from __future__ import annotations

import argparse
import sys

from core.config import load_config
from shopify.utils.cli import add_common_flags, format_output
from shopify.utils.client import ShopifyClient

# Pull the real static method out as a top-level reference. Tests that patch
# `ShopifyClient` in this module's namespace will not replace this alias.
_check_user_errors = ShopifyClient.check_user_errors

_MUTATION = """
mutation ProductUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id title status }
    userErrors { field message }
  }
}
"""


def _build_input(args: argparse.Namespace) -> dict:
    inp: dict = {"id": args.id}
    if args.title is not None:
        inp["title"] = args.title
    if args.description_html is not None:
        inp["descriptionHtml"] = args.description_html
    if args.status is not None:
        inp["status"] = args.status
    if args.tags is not None:
        inp["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]
    if args.vendor is not None:
        inp["vendor"] = args.vendor
    return inp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update a Shopify product.")
    add_common_flags(parser)
    parser.add_argument("--id", required=True, help="Product GID")
    parser.add_argument("--title")
    parser.add_argument(
        "--description-html",
        help="HTML body (Shopify productUpdate.descriptionHtml). Must be valid HTML; not auto-escaped.",
    )
    parser.add_argument("--status", choices=("ACTIVE", "DRAFT", "ARCHIVED"))
    parser.add_argument("--tags", help="Comma-separated tags")
    parser.add_argument("--vendor")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    product_input = _build_input(args)

    if args.dry_run:
        print(format_output(product_input, args.output))
        return 0

    with ShopifyClient(config=cfg) as client:
        data = client.graphql(_MUTATION, {"input": product_input})

    _check_user_errors(data, mutation="productUpdate")
    print(format_output(data["productUpdate"]["product"], args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
