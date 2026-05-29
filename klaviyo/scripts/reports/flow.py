"""Query a Klaviyo flow performance report (POST /flow-values-reports).

Like the campaign report, but the JSON:API ``flow-values-report`` body also
carries an ``interval`` (daily/weekly/monthly). --dry-run prints the body and
skips the POST.
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
        "statistics": list(args.statistic),
        "timeframe": {"key": args.timeframe},
        "conversion_metric_id": args.conversion_metric_id,
        "interval": args.interval,
    }
    if args.filter:
        attributes["filter"] = args.filter
    return {"data": {"type": "flow-values-report", "attributes": attributes}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Query a Klaviyo flow performance report.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument(
        "--statistic",
        action="append",
        required=True,
        help="Statistic to include (repeatable): opens, clicks, revenue, ...",
    )
    parser.add_argument(
        "--timeframe",
        default="last_30_days",
        help="Preset timeframe key (e.g. last_30_days, last_12_months)",
    )
    parser.add_argument(
        "--conversion-metric-id",
        dest="conversion_metric_id",
        required=True,
        help="Conversion metric id (e.g. Placed Order metric)",
    )
    parser.add_argument(
        "--interval",
        default="daily",
        choices=("daily", "weekly", "monthly"),
        help="Reporting interval (default: daily)",
    )
    parser.add_argument("--filter", help="Optional JSON:API filter expression to scope the report")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("flow-values-reports", json=body)

    check_errors(result)
    print(format_output(result.get("data") or {}, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
