"""List Shopify webhook subscriptions with optional topic filter.

Flattens the polymorphic ``endpoint`` field into ``endpoint_kind`` (the
``__typename``) and ``endpoint_target`` (callback URL, ARN, or PubSub
topic) so table output stays readable.
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
query Subs($first: Int!, $topics: [WebhookSubscriptionTopic!]) {
  webhookSubscriptions(first: $first, topics: $topics) {
    edges {
      node {
        id
        topic
        format
        createdAt
        updatedAt
        endpoint {
          __typename
          ... on WebhookHttpEndpoint { callbackUrl }
          ... on WebhookEventBridgeEndpoint { arn }
          ... on WebhookPubSubEndpoint { pubSubProject pubSubTopic }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


def _flatten(node: dict) -> dict:
    endpoint = node.get("endpoint") or {}
    kind = endpoint.get("__typename")
    if kind == "WebhookHttpEndpoint":
        target = endpoint.get("callbackUrl")
    elif kind == "WebhookEventBridgeEndpoint":
        target = endpoint.get("arn")
    elif kind == "WebhookPubSubEndpoint":
        project = endpoint.get("pubSubProject")
        topic = endpoint.get("pubSubTopic")
        target = f"{project}:{topic}" if project or topic else None
    else:
        target = None
    return {
        "id": node.get("id"),
        "topic": node.get("topic"),
        "format": node.get("format"),
        "endpoint_kind": kind,
        "endpoint_target": target,
        "createdAt": node.get("createdAt"),
        "updatedAt": node.get("updatedAt"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Shopify webhook subscriptions.")
    add_common_flags(parser)
    parser.add_argument(
        "--topic",
        help="Optional WebhookSubscriptionTopic filter (e.g. ORDERS_CREATE)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    variables = {
        "first": args.limit,
        "topics": [args.topic] if args.topic else None,
    }

    with ShopifyClient(config=cfg) as client:
        data = client.graphql(_QUERY, variables)

    rows = [_flatten(edge["node"]) for edge in data["webhookSubscriptions"]["edges"]]
    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
