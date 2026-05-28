"""Deep-read a single Shopify product by --id or --handle.

Returns variants, metafields, and (optional) translations.
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
query Product($id: ID, $handle: String, $locale: String) {
  product(id: $id, handle: $handle) {
    id title handle status vendor productType tags
    variants(first: 100) {
      edges { node {
        id sku price inventoryQuantity
        metafields(first: 50) { edges { node { namespace key value type } } }
      } }
    }
    metafields(first: 50) { edges { node { namespace key value type } } }
    translations(locale: $locale) { key value locale }
  }
}
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deep-read a Shopify product.")
    add_common_flags(parser)
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--id", dest="id", help="Product GID")
    selector.add_argument("--handle", help="Product handle")
    parser.add_argument("--locale", help="Locale code for translations")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    variables = {"id": args.id, "handle": args.handle, "locale": args.locale}

    with ShopifyClient(config=cfg) as client:
        data = client.graphql(_QUERY, variables)

    product = data["product"]
    if args.output == "json":
        print(format_output(product, args.output))
    else:
        variants = product.get("variants", {}).get("edges", []) if product else []
        row = {
            "id": product["id"] if product else None,
            "title": product["title"] if product else None,
            "status": product["status"] if product else None,
            "variants": len(variants),
        }
        print(format_output([row], args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
