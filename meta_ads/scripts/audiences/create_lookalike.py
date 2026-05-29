"""Create a lookalike audience from a seed (source) audience.

POST /act_<id>/customaudiences with subtype=LOOKALIKE. The Graph lookalike_spec
JSON carries the target country and the similarity ratio (e.g. 0.01 = closest
1%). --dry-run prints the request; not --yes-gated (no identifier/membership
write — this only defines a derived audience).
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
from meta_ads.utils.client import MetaClient, account_path, check_error


def _build_data(args: argparse.Namespace) -> dict:
    spec = {"country": args.country, "ratio": args.ratio, "type": "similarity"}
    return {
        "name": args.name,
        "subtype": "LOOKALIKE",
        "origin_audience_id": args.source_audience_id,
        "lookalike_spec": json.dumps(spec),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a lookalike audience.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument("--name", required=True, help="Lookalike audience name")
    parser.add_argument(
        "--source-audience-id",
        dest="source_audience_id",
        required=True,
        help="Seed (origin) custom-audience id",
    )
    parser.add_argument("--country", required=True, help="Target country code (e.g. US, SE)")
    parser.add_argument(
        "--ratio",
        type=float,
        required=True,
        help="Similarity ratio in (0, 0.2] (e.g. 0.01 = closest 1%%)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if not 0 < args.ratio <= 0.2:
        parser.error("--ratio must be in the range (0, 0.2]")

    path = f"{account_path(args.account_id)}/customaudiences"
    data = _build_data(args)

    if args.dry_run:
        print(format_output({"method": "POST", "path": path, "data": data}, args.output))
        return 0

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.post(path, data=data)

    check_error(result)
    print(format_output({"id": result.get("id"), "name": args.name}, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
