"""Auth smoke test. Prints shop name, primary domain, and plan."""

from __future__ import annotations

import argparse
import json
import sys

from core.config import load_config
from shopify.utils.client import ShopifyClient

_QUERY = """
query { shop { name primaryDomain { url } plan { displayName } } }
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Shopify Admin API authentication.")
    parser.add_argument("--config", default="store-config.yaml", help="Path to store-config.yaml")
    parser.add_argument("--output", choices=("table", "json"), default="table")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    client = ShopifyClient(config=cfg)
    try:
        data = client.graphql(_QUERY)
    finally:
        client.close()

    shop = data["shop"]
    if args.output == "json":
        print(json.dumps(shop, indent=2))
    else:
        print(f"Shop:    {shop['name']}")
        print(f"Domain:  {shop['primaryDomain']['url']}")
        print(f"Plan:    {shop['plan']['displayName']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
