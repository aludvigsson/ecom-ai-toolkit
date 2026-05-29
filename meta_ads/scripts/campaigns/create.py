"""Create a campaign under an ad account — always PAUSED.

POST /act_<id>/campaigns. The created campaign's ``status`` is hard-coded to
``PAUSED``; there is no flag that yields ``ACTIVE`` (a deliberate guardrail
against accidental spend — activate with campaigns/activate.py, which is
--yes-gated). --dry-run prints the Graph node/edge + form body and skips the POST.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import json

from core.config import load_config
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, account_path, check_error


def _build_data(args: argparse.Namespace) -> dict:
    data: dict[str, object] = {
        "name": args.name,
        "objective": args.objective,
        # Safe-default guardrail: never ACTIVE on create.
        "status": "PAUSED",
        "special_ad_categories": json.dumps(args.special_ad_categories or []),
    }
    if args.buying_type:
        data["buying_type"] = args.buying_type
    if args.daily_budget is not None:
        data["daily_budget"] = args.daily_budget
    if args.lifetime_budget is not None:
        data["lifetime_budget"] = args.lifetime_budget
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a PAUSED campaign.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument("--name", required=True, help="Campaign name")
    parser.add_argument(
        "--objective",
        required=True,
        help="Campaign objective (e.g. OUTCOME_SALES, OUTCOME_TRAFFIC)",
    )
    parser.add_argument(
        "--buying_type",
        dest="buying_type",
        help="Buying type (e.g. AUCTION)",
    )
    parser.add_argument(
        "--daily-budget",
        dest="daily_budget",
        type=int,
        help="Daily budget in account minor units (e.g. cents)",
    )
    parser.add_argument(
        "--lifetime-budget",
        dest="lifetime_budget",
        type=int,
        help="Lifetime budget in account minor units (e.g. cents)",
    )
    parser.add_argument(
        "--special-ad-categories",
        dest="special_ad_categories",
        action="append",
        help="Special ad category (repeatable; e.g. HOUSING, EMPLOYMENT, CREDIT)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    path = f"{account_path(args.account_id)}/campaigns"
    data = _build_data(args)

    if args.dry_run:
        print(format_output({"path": path, "data": data}, args.output))
        return 0

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.post(path, data=data)

    check_error(result)
    print(format_output(result, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
