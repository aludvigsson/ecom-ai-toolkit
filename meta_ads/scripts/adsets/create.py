"""Create an ad set under an ad account — always PAUSED.

POST /act_<id>/adsets. Forces status=PAUSED (no ACTIVE path; activate with
adsets/activate.py, --yes-gated). The targeting spec is a raw JSON string (the
Graph form convention); it is validated as JSON but forwarded unchanged.
--dry-run prints the node/edge + form body and skips the POST.
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
        "campaign_id": args.campaign_id,
        "billing_event": args.billing_event,
        "optimization_goal": args.optimization_goal,
        "targeting": args.targeting,
        # Safe-default guardrail: never ACTIVE on create.
        "status": "PAUSED",
    }
    if args.daily_budget is not None:
        data["daily_budget"] = args.daily_budget
    if args.lifetime_budget is not None:
        data["lifetime_budget"] = args.lifetime_budget
    if args.bid_amount is not None:
        data["bid_amount"] = args.bid_amount
    if args.start_time:
        data["start_time"] = args.start_time
    if args.end_time:
        data["end_time"] = args.end_time
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a PAUSED ad set.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument("--name", required=True, help="Ad set name")
    parser.add_argument("--campaign-id", dest="campaign_id", required=True)
    parser.add_argument(
        "--billing-event", dest="billing_event", required=True, help="e.g. IMPRESSIONS"
    )
    parser.add_argument(
        "--optimization-goal",
        dest="optimization_goal",
        required=True,
        help="e.g. LINK_CLICKS, OFFSITE_CONVERSIONS",
    )
    parser.add_argument("--targeting", required=True, help="Targeting spec as a JSON string")
    parser.add_argument(
        "--daily-budget", dest="daily_budget", type=int, help="Daily budget (minor units)"
    )
    parser.add_argument(
        "--lifetime-budget",
        dest="lifetime_budget",
        type=int,
        help="Lifetime budget (minor units)",
    )
    parser.add_argument(
        "--bid-amount", dest="bid_amount", type=int, help="Bid amount (minor units)"
    )
    parser.add_argument("--start-time", dest="start_time", help="ISO 8601 start time")
    parser.add_argument("--end-time", dest="end_time", help="ISO 8601 end time")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if args.daily_budget is None and args.lifetime_budget is None:
        parser.error("one of --daily-budget or --lifetime-budget is required")
    try:
        json.loads(args.targeting)
    except json.JSONDecodeError as exc:
        parser.error(f"--targeting is not valid JSON: {exc}")

    path = f"{account_path(args.account_id)}/adsets"
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
