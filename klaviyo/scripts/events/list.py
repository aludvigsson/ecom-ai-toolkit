"""List Klaviyo events with optional filters.

Filters: --metric-id, --profile-id, --since (ISO-8601 lower bound). When more
than one is given they are combined with a JSON:API ``and(...)`` expression.
Flattens event resources into flat rows; honors --limit via pagination.
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
from klaviyo.utils.client import KlaviyoClient


def _flatten(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "datetime": attrs.get("datetime"),
        "timestamp": attrs.get("timestamp"),
        "uuid": attrs.get("uuid"),
    }


def _build_filter(args: argparse.Namespace) -> str | None:
    clauses: list[str] = []
    if args.metric_id:
        clauses.append(f'equals(metric_id,"{args.metric_id}")')
    if args.profile_id:
        clauses.append(f'equals(profile_id,"{args.profile_id}")')
    if args.since:
        clauses.append(f"greater-or-equal(datetime,{args.since})")
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return f"and({','.join(clauses)})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Klaviyo events.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--metric-id", dest="metric_id", help="Filter by metric id")
    parser.add_argument("--profile-id", dest="profile_id", help="Filter by profile id")
    parser.add_argument(
        "--since", help="Lower bound on event datetime (ISO-8601), e.g. 2026-01-01T00:00:00Z"
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    params: dict[str, object] = {}
    flt = _build_filter(args)
    if flt:
        params["filter"] = flt

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        rows = [_flatten(r) for r in client.paginate("events", params=params, limit=args.limit)]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
