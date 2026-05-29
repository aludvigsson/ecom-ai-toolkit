"""List campaigns under an ad account.

GET /act_<id>/campaigns with field selection, optional --status effective-status
filter (Graph wants a JSON-array string), and cursor pagination capped by --limit.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import json
import sys

from core.config import load_config
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, account_path

_FIELDS = (
    "id,name,objective,status,effective_status,buying_type,"
    "daily_budget,lifetime_budget,start_time,stop_time"
)


def _flatten(node: dict) -> dict:
    return {
        "id": node.get("id"),
        "name": node.get("name"),
        "objective": node.get("objective"),
        "status": node.get("status"),
        "effective_status": node.get("effective_status"),
        "daily_budget": node.get("daily_budget"),
        "lifetime_budget": node.get("lifetime_budget"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List campaigns under an ad account.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument(
        "--status",
        help="Filter by effective_status (e.g. ACTIVE, PAUSED, ARCHIVED)",
    )
    parser.add_argument("--fields", default=_FIELDS)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    params: dict[str, object] = {"fields": args.fields}
    if args.status:
        params["effective_status"] = json.dumps([args.status])

    cfg = load_config(args.config)
    path = f"{account_path(args.account_id)}/campaigns"
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        rows = [_flatten(n) for n in client.paginate(path, params=params, limit=args.limit)]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
