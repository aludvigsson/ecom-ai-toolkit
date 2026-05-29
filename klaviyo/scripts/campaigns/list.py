"""List Klaviyo campaigns.

Klaviyo's /campaigns endpoint requires a filter on messages.channel; this
script defaults it to "email" and exposes --channel. Flattens JSON:API campaign
resources into flat rows and honors --limit via cursor pagination.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse

from core.config import load_config
from klaviyo.utils.cli import (
    add_common_flags,
    add_klaviyo_flags,
    configure_logging_from_args,
    format_output,
)
from klaviyo.utils.client import KlaviyoClient


def _flatten(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "name": attrs.get("name"),
        "status": attrs.get("status"),
        "created_at": attrs.get("created_at"),
        "scheduled_at": attrs.get("scheduled_at"),
        "send_time": attrs.get("send_time"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Klaviyo campaigns.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument(
        "--channel",
        default="email",
        help="Message channel to filter by (Klaviyo requires this; default email)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    params = {"filter": f'equals(messages.channel,"{args.channel}")'}

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        rows = [_flatten(r) for r in client.paginate("campaigns", params=params, limit=args.limit)]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
