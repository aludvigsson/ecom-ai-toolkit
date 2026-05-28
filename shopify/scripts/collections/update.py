"""Update a Shopify collection.

Builds CollectionInput from non-None CLI flags so we don't blank fields the
user didn't touch. Honors --dry-run by printing the would-be input and
exiting 0 without calling the mutation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.config import load_config
from shopify.utils.cli import add_common_flags, format_output
from shopify.utils.client import ShopifyClient, check_user_errors

_MUTATION = """
mutation CollectionUpdate($input: CollectionInput!) {
  collectionUpdate(input: $input) {
    collection { id title handle }
    userErrors { field message }
  }
}
"""

_SORT_ORDERS = (
    "ALPHA_ASC",
    "ALPHA_DESC",
    "BEST_SELLING",
    "CREATED",
    "CREATED_DESC",
    "MANUAL",
    "PRICE_ASC",
    "PRICE_DESC",
)


def _build_input(args: argparse.Namespace) -> dict:
    inp: dict = {"id": args.id}
    if args.title is not None:
        inp["title"] = args.title
    if args.handle is not None:
        inp["handle"] = args.handle
    if args.description_html is not None:
        inp["descriptionHtml"] = args.description_html
    if args.sort_order is not None:
        inp["sortOrder"] = args.sort_order
    if args.rules is not None:
        rules_data = json.loads(Path(args.rules).read_text(encoding="utf-8"))
        inp["ruleSet"] = {
            "appliedDisjunctively": rules_data["appliedDisjunctively"],
            "rules": rules_data["rules"],
        }
    return inp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update a Shopify collection.")
    add_common_flags(parser)
    parser.add_argument("--id", required=True, help="Collection GID")
    parser.add_argument("--title")
    parser.add_argument("--handle")
    parser.add_argument("--description-html", help="HTML body; not auto-escaped")
    parser.add_argument(
        "--rules",
        help="Path to JSON ruleSet file (for smart collections)",
    )
    parser.add_argument("--sort-order", choices=_SORT_ORDERS)
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    collection_input = _build_input(args)

    if args.dry_run:
        print(format_output(collection_input, args.output))
        return 0

    with ShopifyClient(config=cfg) as client:
        data = client.graphql(_MUTATION, {"input": collection_input})

    check_user_errors(data, mutation="collectionUpdate")
    print(format_output(data["collectionUpdate"]["collection"], args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
