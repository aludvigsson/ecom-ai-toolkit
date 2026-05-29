"""List the ad accounts owned by a business (or accessible to the token).

Parent node resolution: --business-id, else the ``META_BUSINESS_ID`` secret,
else ``me/adaccounts``. Flattens Graph ad account nodes into flat rows and
honors --limit via cursor pagination.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from core.secrets import get_secret
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient

_FIELDS = "id,account_id,name,account_status,currency,timezone_name,amount_spent"


def _flatten(node: dict) -> dict:
    return {
        "id": node.get("id"),
        "account_id": node.get("account_id"),
        "name": node.get("name"),
        "account_status": node.get("account_status"),
        "currency": node.get("currency"),
        "timezone_name": node.get("timezone_name"),
        "amount_spent": node.get("amount_spent"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Meta ad accounts.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument(
        "--business-id",
        dest="business_id",
        help="Business id whose owned_ad_accounts to list (default: config or /me)",
    )
    parser.add_argument(
        "--fields",
        default=_FIELDS,
        help="Comma-separated Graph fields to request",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    business_id = args.business_id or get_secret("META_BUSINESS_ID")
    path = f"{business_id}/owned_ad_accounts" if business_id else "me/adaccounts"
    params = {"fields": args.fields}

    with MetaClient(config=cfg, api_version=args.api_version) as client:
        rows = [_flatten(n) for n in client.paginate(path, params=params, limit=args.limit)]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
