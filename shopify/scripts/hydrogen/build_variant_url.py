"""Hydrogen-aware variant URL builder.

Reads store-config.yaml to determine the Hydrogen storefront URL pattern,
then composes the canonical URL for a given (product_handle, variant) +
market. Bare Shopify handles like ``/products/<handle>`` do NOT resolve
on Hydrogen storefronts -- variant slugs (or query params) are required.

This script does NOT hit Shopify Admin API. Pure local URL construction.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import json
import urllib.parse as _urlparse

from core.config import load_config
from core.logging import get_logger
from shopify.utils.cli import add_common_flags, configure_logging_from_args

_log = get_logger("ecom.shopify.hydrogen.build_variant_url")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a Hydrogen-aware variant URL from a product handle + variant id/sku + market."
        ),
    )
    add_common_flags(parser)
    parser.add_argument("--handle", required=True, help="Product handle (e.g. 'pearl-classic')")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--variant-id",
        dest="variant_id",
        help="Numeric Shopify variant ID (e.g. '42949672960123')",
    )
    group.add_argument(
        "--variant-sku",
        dest="variant_sku",
        help="Variant SKU (used as a query param)",
    )
    parser.add_argument(
        "--market",
        help="Market code from store-config.yaml. Defaults to the market with primary locale.",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)

    if cfg.store.storefront_type != "hydrogen":
        print(
            f"Error: store-config.yaml says storefront_type={cfg.store.storefront_type!r}. "
            f"This script is for Hydrogen storefronts. For Online Store 2.0 use "
            f"shopify/scripts/theme/.",
            file=sys.stderr,
        )
        return 1

    if args.market:
        market = cfg.market(args.market)
    else:
        default_locale = cfg.store.default_locale
        default = next((m for m in cfg.markets if m.locale == default_locale), None)
        if default is None:
            print(
                "Error: --market not provided and no market matches store.default_locale. "
                "Pass --market <code> explicitly.",
                file=sys.stderr,
            )
            return 1
        market = default

    domain = cfg.store.primary_domain.rstrip("/")
    prefix = market.url_prefix.rstrip("/")
    handle = args.handle
    encoded_handle = _urlparse.quote(handle, safe="-_~")

    if args.variant_id:
        url = f"https://{domain}{prefix}/products/{encoded_handle}?variant={args.variant_id}"
    else:
        url = f"https://{domain}{prefix}/products/{encoded_handle}?sku={args.variant_sku}"

    if args.output == "json":
        print(json.dumps({"url": url, "market": market.code, "handle": handle}, indent=2))
    else:
        print(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
