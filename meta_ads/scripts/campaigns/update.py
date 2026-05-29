"""Update a campaign — POST /<campaign_id>.

Sends only the fields given. A budget change (--daily-budget/--lifetime-budget)
is --yes-gated (errors before the network call without --yes and not --dry-run);
a name-only update is not gated. --dry-run prints the body and skips the POST.
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
from meta_ads.utils.client import MetaClient, check_error


def _build_data(args: argparse.Namespace) -> dict:
    data: dict[str, object] = {}
    if args.name is not None:
        data["name"] = args.name
    if args.status is not None:
        data["status"] = args.status
    if args.daily_budget is not None:
        data["daily_budget"] = args.daily_budget
    if args.lifetime_budget is not None:
        data["lifetime_budget"] = args.lifetime_budget
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update a campaign.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Campaign id")
    parser.add_argument("--name", help="New campaign name")
    parser.add_argument(
        "--status",
        choices=("PAUSED", "ARCHIVED"),
        help="New status (use pause.py/activate.py for PAUSED/ACTIVE flips)",
    )
    parser.add_argument(
        "--daily-budget", dest="daily_budget", type=int, help="Daily budget (minor units)"
    )
    parser.add_argument(
        "--lifetime-budget",
        dest="lifetime_budget",
        type=int,
        help="Lifetime budget (minor units)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    data = _build_data(args)
    if not data:
        parser.error("nothing to update; pass --name/--status/--daily-budget/--lifetime-budget")

    changes_budget = args.daily_budget is not None or args.lifetime_budget is not None

    if args.dry_run:
        print(format_output({"path": args.id, "data": data}, args.output))
        return 0

    if changes_budget and not args.yes:
        parser.error("changing a campaign budget affects spend; pass --yes to confirm")

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.post(args.id, data=data)

    check_error(result)
    print(format_output(result, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
