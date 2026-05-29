"""Query a Klaviyo metric aggregate (POST /metric-aggregates).

A read-style query expressed as a JSON:API ``metric-aggregate`` body: the
metric id, one or more measurements, an interval, and a datetime window encoded
as JSON:API filter expressions. --dry-run prints the body and skips the POST.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from klaviyo.utils.cli import (
    add_common_flags,
    add_klaviyo_flags,
    configure_logging_from_args,
    format_output,
)
from klaviyo.utils.client import KlaviyoClient, check_errors


def _build_body(args: argparse.Namespace) -> dict:
    attributes: dict[str, object] = {
        "metric_id": args.metric_id,
        "measurements": list(args.measurement),
        "interval": args.interval,
        "filter": [
            f"greater-or-equal(datetime,{args.start})",
            f"less-than(datetime,{args.end})",
        ],
    }
    if args.timezone:
        attributes["timezone"] = args.timezone
    return {"data": {"type": "metric-aggregate", "attributes": attributes}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Query a Klaviyo metric aggregate.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--metric-id", dest="metric_id", required=True, help="Metric id")
    parser.add_argument(
        "--measurement",
        action="append",
        required=True,
        help="Measurement to aggregate (repeatable): count, sum_value, unique, ...",
    )
    parser.add_argument(
        "--interval",
        default="day",
        choices=("hour", "day", "week", "month"),
        help="Aggregation interval (default: day)",
    )
    parser.add_argument(
        "--start",
        required=True,
        help="ISO-8601 window start (inclusive), e.g. 2026-01-01T00:00:00Z",
    )
    parser.add_argument(
        "--end",
        required=True,
        help="ISO-8601 window end (exclusive), e.g. 2026-01-31T00:00:00Z",
    )
    parser.add_argument("--timezone", help="IANA timezone for bucketing, e.g. UTC")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("metric-aggregates", json=body)

    check_errors(result)
    print(format_output(result.get("data") or {}, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
