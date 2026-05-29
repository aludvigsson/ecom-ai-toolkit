"""Get a single Meta ad account by --account-id (with or without act_ prefix)."""

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
from meta_ads.utils.client import MetaClient, account_path, check_error

_FIELDS = (
    "id,account_id,name,account_status,currency,timezone_name,"
    "amount_spent,balance,business_name,spend_cap"
)


def _flatten(node: dict) -> dict:
    return {
        "id": node.get("id"),
        "account_id": node.get("account_id"),
        "name": node.get("name"),
        "account_status": node.get("account_status"),
        "currency": node.get("currency"),
        "timezone_name": node.get("timezone_name"),
        "amount_spent": node.get("amount_spent"),
        "balance": node.get("balance"),
        "spend_cap": node.get("spend_cap"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get a Meta ad account.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument("--fields", default=_FIELDS)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        body = client.get(account_path(args.account_id), params={"fields": args.fields})

    check_error(body)
    print(format_output(_flatten(body), args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
