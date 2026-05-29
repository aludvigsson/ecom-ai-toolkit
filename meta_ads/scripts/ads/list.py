"""List ads under an account or one ad set.

Exactly one parent is required: --account-id (GET /act_<id>/ads) or --adset-id
(GET /<adset_id>/ads). Field selection + cursor pagination.
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

_FIELDS = "id,name,adset_id,campaign_id,status,effective_status,creative"


def _flatten(node: dict) -> dict:
    creative = node.get("creative") or {}
    return {
        "id": node.get("id"),
        "name": node.get("name"),
        "adset_id": node.get("adset_id"),
        "campaign_id": node.get("campaign_id"),
        "status": node.get("status"),
        "effective_status": node.get("effective_status"),
        "creative_id": creative.get("id"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List ads.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id")
    parser.add_argument("--adset-id", dest="adset_id")
    parser.add_argument("--fields", default=_FIELDS)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if bool(args.account_id) == bool(args.adset_id):
        parser.error("exactly one of --account-id or --adset-id is required")

    path = f"{account_path(args.account_id)}/ads" if args.account_id else f"{args.adset_id}/ads"

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        rows = [
            _flatten(n)
            for n in client.paginate(path, params={"fields": args.fields}, limit=args.limit)
        ]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
