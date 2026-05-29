"""Get a single custom audience node by --id."""

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
from meta_ads.utils.client import MetaClient, check_error

_FIELDS = (
    "id,name,subtype,description,rule,retention_days,"
    "approximate_count_lower_bound,approximate_count_upper_bound,"
    "operation_status,delivery_status,data_source,lookalike_spec,"
    "time_created,time_updated"
)


def _flatten(node: dict) -> dict:
    op = node.get("operation_status") or {}
    return {
        "id": node.get("id"),
        "name": node.get("name"),
        "subtype": node.get("subtype"),
        "description": node.get("description"),
        "retention_days": node.get("retention_days"),
        "count_lower": node.get("approximate_count_lower_bound"),
        "count_upper": node.get("approximate_count_upper_bound"),
        "operation_status": op.get("description"),
        "time_updated": node.get("time_updated"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get a custom audience by id.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Custom audience id")
    parser.add_argument("--fields", default=_FIELDS)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        body = client.get(args.id, params={"fields": args.fields})

    check_error(body)
    print(format_output(_flatten(body), args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
