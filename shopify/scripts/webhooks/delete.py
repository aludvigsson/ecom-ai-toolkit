"""Delete a Shopify webhook subscription by ID.

Destructive: requires ``--yes`` to actually run the mutation. ``--dry-run``
prints the intended deletion and exits 0 without requiring ``--yes``.
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

_MUTATION = """
mutation Delete($id: ID!) {
  webhookSubscriptionDelete(id: $id) {
    deletedWebhookSubscriptionId
    userErrors { field message }
  }
}
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Delete a Shopify webhook subscription by ID.")
    add_common_flags(parser)
    parser.add_argument("--id", required=True, help="WebhookSubscription GID")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm destructive deletion (required for live execution)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if args.dry_run:
        print(f"Would delete webhook subscription {args.id}")
        return 0

    if not args.yes:
        parser.error("--yes is required to confirm deletion; aborting")

    cfg = load_config(args.config)
    with ShopifyClient(config=cfg) as client:
        data = client.graphql(_MUTATION, {"id": args.id})

    check_user_errors(data, mutation="webhookSubscriptionDelete")
    print(f"Deleted: {data['webhookSubscriptionDelete']['deletedWebhookSubscriptionId']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
