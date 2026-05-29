"""Get a single ad node by --id."""

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
    "id,name,adset_id,campaign_id,account_id,status,effective_status,"
    "creative,tracking_specs,created_time,updated_time"
)


def _flatten(node: dict) -> dict:
    creative = node.get("creative") or {}
    return {
        "id": node.get("id"),
        "name": node.get("name"),
        "adset_id": node.get("adset_id"),
        "campaign_id": node.get("campaign_id"),
        "account_id": node.get("account_id"),
        "status": node.get("status"),
        "effective_status": node.get("effective_status"),
        "creative_id": creative.get("id"),
        "created_time": node.get("created_time"),
        "updated_time": node.get("updated_time"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get an ad by id.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Ad id")
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
