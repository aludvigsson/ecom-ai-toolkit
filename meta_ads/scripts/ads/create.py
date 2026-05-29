"""Create an ad under an ad account — always PAUSED.

POST /act_<id>/ads. Forces status=PAUSED (no ACTIVE path; activate with
ads/activate.py, --yes-gated). An ad ties an ad set to a creative: --adset-id
plus --creative-id (sent as the Graph ``creative`` form param,
{"creative_id": ...} JSON). --dry-run prints the node/edge + form and skips POST.
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a PAUSED ad.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument("--name", required=True, help="Ad name")
    parser.add_argument("--adset-id", dest="adset_id", required=True)
    parser.add_argument(
        "--creative-id", dest="creative_id", required=True, help="Existing ad creative id"
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    path = f"{account_path(args.account_id)}/ads"
    data = {
        "name": args.name,
        "adset_id": args.adset_id,
        "creative": json.dumps({"creative_id": args.creative_id}),
        # Safe-default guardrail: never ACTIVE on create.
        "status": "PAUSED",
    }

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
