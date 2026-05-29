"""Delete a Klaviyo campaign by id.

Destructive: requires --yes for live execution. --dry-run prints the intended
deletion and exits 0 without requiring --yes.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from klaviyo.utils.cli import add_common_flags, add_klaviyo_flags, configure_logging_from_args
from klaviyo.utils.client import KlaviyoClient, check_errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Delete a Klaviyo campaign by id.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Campaign id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if args.dry_run:
        print(f"Would delete campaign {args.id}")
        return 0

    if not args.yes:
        parser.error("--yes is required to confirm deletion; aborting")

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.delete(f"campaigns/{args.id}")

    check_errors(result)
    print(f"Deleted: {args.id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
