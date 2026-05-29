"""Query Meta Ads insights for an account or any structure node.

GET /<object_id>/insights. The object node is the account (--account-id, via
act_<id>) or any campaign/adset/ad node (--object-id). Supports --level, a
--date-preset OR a --since/--until time range (mutually exclusive), comma-joined
--breakdowns, and comma-joined --fields. Insights rows are already flat metric
dicts, so each row is emitted as-is (capped by --limit via cursor pagination).
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import json
import sys

from core.config import load_config
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, account_path

_DEFAULT_FIELDS = (
    "impressions,reach,clicks,spend,cpc,cpm,ctr,frequency,actions,cost_per_action_type"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Query Meta Ads insights.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument(
        "--account-id",
        dest="account_id",
        help="Ad account id (insights node is act_<id>)",
    )
    parser.add_argument(
        "--object-id",
        dest="object_id",
        help="Any campaign/adset/ad node id to pull insights for",
    )
    parser.add_argument(
        "--level",
        choices=("account", "campaign", "adset", "ad"),
        default="account",
        help="Aggregation level of the returned rows",
    )
    parser.add_argument(
        "--date-preset",
        dest="date_preset",
        default="last_30d",
        help="Graph date_preset (ignored when --since/--until are given)",
    )
    parser.add_argument("--since", help="Start date YYYY-MM-DD (requires --until)")
    parser.add_argument("--until", help="End date YYYY-MM-DD (requires --since)")
    parser.add_argument(
        "--breakdowns",
        help="Comma-separated Graph breakdowns (e.g. age,gender)",
    )
    parser.add_argument("--fields", default=_DEFAULT_FIELDS)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if bool(args.account_id) == bool(args.object_id):
        parser.error("exactly one of --account-id or --object-id is required")
    if bool(args.since) != bool(args.until):
        parser.error("--since and --until must be given together")

    node = account_path(args.account_id) if args.account_id else args.object_id
    path = f"{node}/insights"

    params: dict[str, object] = {
        "level": args.level,
        "fields": args.fields,
    }
    if args.since and args.until:
        params["time_range"] = json.dumps({"since": args.since, "until": args.until})
    else:
        params["date_preset"] = args.date_preset
    if args.breakdowns:
        params["breakdowns"] = args.breakdowns

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        rows = list(client.paginate(path, params=params, limit=args.limit))

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
