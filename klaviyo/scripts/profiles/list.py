"""List Klaviyo profiles with optional filters.

Filters: --email (exact), --list-id (membership), --segment-id (membership).
Flattens JSON:API profile resources into flat rows (id + common attributes).
Honors --limit via the client's cursor pagination.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

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
        "email": attrs.get("email"),
        "phone_number": attrs.get("phone_number"),
        "first_name": attrs.get("first_name"),
        "last_name": attrs.get("last_name"),
        "created": attrs.get("created"),
        "updated": attrs.get("updated"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Klaviyo profiles.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--email", help="Filter to the profile with this exact email")
    parser.add_argument("--list-id", dest="list_id", help="List membership to filter by")
    parser.add_argument("--segment-id", dest="segment_id", help="Segment membership to filter by")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    path = "profiles"
    params: dict[str, object] = {}
    if args.email:
        params["filter"] = f'equals(email,"{args.email}")'
    if args.list_id:
        path = f"lists/{args.list_id}/profiles"
    if args.segment_id:
        path = f"segments/{args.segment_id}/profiles"

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        rows = [_flatten(r) for r in client.paginate(path, params=params, limit=args.limit)]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
