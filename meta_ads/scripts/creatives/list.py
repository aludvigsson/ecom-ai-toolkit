"""List ad creatives under an ad account (GET /act_<id>/adcreatives)."""

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

_FIELDS = "id,name,object_type,status,thumbnail_url,image_hash"


def _flatten(node: dict) -> dict:
    return {
        "id": node.get("id"),
        "name": node.get("name"),
        "object_type": node.get("object_type"),
        "status": node.get("status"),
        "thumbnail_url": node.get("thumbnail_url"),
        "image_hash": node.get("image_hash"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List ad creatives.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument("--fields", default=_FIELDS)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    path = f"{account_path(args.account_id)}/adcreatives"
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        rows = [
            _flatten(n)
            for n in client.paginate(path, params={"fields": args.fields}, limit=args.limit)
        ]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
