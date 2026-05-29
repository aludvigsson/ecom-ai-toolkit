"""Activate a campaign — POST /<campaign_id> with status=ACTIVE.

The only script that ever sends status=ACTIVE. --yes-gated: without --yes (and
not --dry-run) it errors before any network call. --dry-run prints the node +
form and skips the POST (allowed without --yes, since it touches nothing).
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Activate a campaign (--yes required).")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Campaign id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    path = args.id
    data = {"status": "ACTIVE"}

    if args.dry_run:
        print(format_output({"path": path, "data": data}, args.output))
        return 0

    if not args.yes:
        parser.error("activating a campaign spends money; pass --yes to confirm")

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.post(path, data=data)

    check_error(result)
    print(format_output(result, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
