"""List custom audiences under an ad account.

GET /act_<id>/customaudiences with field selection and cursor pagination capped
by --limit. Flattens audience nodes into flat rows for table output.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
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
    "id,name,subtype,description,approximate_count_lower_bound,"
    "approximate_count_upper_bound,operation_status,delivery_status,"
    "time_created,time_updated"
)


def _flatten(node: dict) -> dict:
    op = node.get("operation_status") or {}
    return {
        "id": node.get("id"),
        "name": node.get("name"),
        "subtype": node.get("subtype"),
        "count_lower": node.get("approximate_count_lower_bound"),
        "count_upper": node.get("approximate_count_upper_bound"),
        "operation_status": op.get("description"),
        "time_updated": node.get("time_updated"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List custom audiences under an ad account.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument("--fields", default=_FIELDS)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    path = f"{account_path(args.account_id)}/customaudiences"
    params = {"fields": args.fields}
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        rows = [_flatten(n) for n in client.paginate(path, params=params, limit=args.limit)]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
