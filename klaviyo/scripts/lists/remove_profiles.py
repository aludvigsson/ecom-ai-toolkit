"""Remove profiles from a Klaviyo list via the relationships endpoint.

High-stakes: --yes is required for live execution. --dry-run works without
--yes and prints the body without calling the API.
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Remove profiles from a Klaviyo list.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="List id")
    parser.add_argument(
        "--profile-id",
        dest="profile_ids",
        action="append",
        required=True,
        help="Profile id to remove (repeatable)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = {"data": [{"type": "profile", "id": pid} for pid in args.profile_ids]}

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    if not args.yes:
        parser.error("--yes is required to confirm removal; aborting")

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.delete(f"lists/{args.id}/relationships/profiles", json=body)

    check_errors(result)
    print(f"Removed {len(args.profile_ids)} profile(s) from list {args.id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
