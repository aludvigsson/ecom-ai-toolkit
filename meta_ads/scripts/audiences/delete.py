"""Delete a custom audience.

Destructive: requires --yes to actually run the deletion. --dry-run prints the
intended deletion and exits 0 without requiring --yes.
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
    parser = argparse.ArgumentParser(description="Delete a custom audience.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Custom audience id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if args.dry_run:
        print(format_output({"method": "DELETE", "path": args.id}, args.output))
        return 0

    if not args.yes:
        parser.error("--yes is required to confirm deletion; aborting")

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.delete(args.id)

    check_error(result)
    print(format_output({"deleted": args.id, "result": result}, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
