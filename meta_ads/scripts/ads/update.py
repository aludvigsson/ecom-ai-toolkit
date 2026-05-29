"""Update an ad — POST /<ad_id>.

Sends only the fields given: --name and/or a creative swap (--creative-id, sent
as the Graph ``creative`` form param). No ad-level budget, so no budget gate.
--dry-run prints the body and skips the POST.
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
from meta_ads.utils.client import MetaClient, check_error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update an ad.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Ad id")
    parser.add_argument("--name", help="New ad name")
    parser.add_argument(
        "--creative-id", dest="creative_id", help="Swap to this existing creative id"
    )
    parser.add_argument(
        "--status",
        choices=("PAUSED", "ARCHIVED"),
        help="New status (use pause.py/activate.py for PAUSED/ACTIVE flips)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    data: dict[str, object] = {}
    if args.name is not None:
        data["name"] = args.name
    if args.status is not None:
        data["status"] = args.status
    if args.creative_id is not None:
        data["creative"] = json.dumps({"creative_id": args.creative_id})
    if not data:
        parser.error("nothing to update; pass --name/--creative-id/--status")

    if args.dry_run:
        print(format_output({"path": args.id, "data": data}, args.output))
        return 0

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.post(args.id, data=data)

    check_error(result)
    print(format_output(result, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
