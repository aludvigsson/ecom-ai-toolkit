"""List Klaviyo flows.

Optional --status filter (e.g. ``live``, ``draft``, ``manual``). Flattens
JSON:API flow resources into flat rows. Honors --limit via cursor pagination.
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
        "name": attrs.get("name"),
        "status": attrs.get("status"),
        "archived": attrs.get("archived"),
        "trigger_type": attrs.get("trigger_type"),
        "created": attrs.get("created"),
        "updated": attrs.get("updated"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Klaviyo flows.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--status", help="Filter by flow status (e.g. live, draft, manual)")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    params: dict[str, object] = {}
    if args.status:
        params["filter"] = f'equals(status,"{args.status}")'

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        rows = [_flatten(r) for r in client.paginate("flows", params=params, limit=args.limit)]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
