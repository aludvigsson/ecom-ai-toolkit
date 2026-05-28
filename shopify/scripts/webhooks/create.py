"""Create a Shopify HTTP webhook subscription.

Calls ``webhookSubscriptionCreate`` with a ``WebhookSubscriptionInput``
containing the callback URL and payload format. ``--callback-url`` must
be HTTPS; the parser errors at parse time otherwise. ``--dry-run`` prints
the would-be input and skips the mutation.
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
from shopify.utils.client import ShopifyClient, check_user_errors

_MUTATION = """
mutation Create($topic: WebhookSubscriptionTopic!, $input: WebhookSubscriptionInput!) {
  webhookSubscriptionCreate(topic: $topic, webhookSubscription: $input) {
    webhookSubscription { id topic format }
    userErrors { field message }
  }
}
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a Shopify webhook subscription.")
    add_common_flags(parser)
    parser.add_argument(
        "--topic",
        required=True,
        help="WebhookSubscriptionTopic (e.g. ORDERS_CREATE)",
    )
    parser.add_argument(
        "--callback-url",
        dest="callback_url",
        required=True,
        help="HTTPS callback URL",
    )
    parser.add_argument(
        "--format",
        dest="payload_format",
        choices=("JSON", "XML"),
        default="JSON",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if not args.callback_url.startswith("https://"):
        parser.error("--callback-url must start with https://")

    inp = {
        "callbackUrl": args.callback_url,
        "format": args.payload_format,
    }

    if args.dry_run:
        print(format_output({"topic": args.topic, "input": inp}, args.output))
        return 0

    cfg = load_config(args.config)
    with ShopifyClient(config=cfg) as client:
        data = client.graphql(_MUTATION, {"topic": args.topic, "input": inp})

    check_user_errors(data, mutation="webhookSubscriptionCreate")
    sub = data["webhookSubscriptionCreate"]["webhookSubscription"] or {}
    print(format_output(sub, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
