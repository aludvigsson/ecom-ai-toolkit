"""Unsubscribe a profile from a list's marketing (consent removal).

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


def _build_body(args: argparse.Namespace) -> dict:
    profile_attrs: dict[str, object] = {}
    if args.email:
        profile_attrs["email"] = args.email
    if args.phone_number:
        profile_attrs["phone_number"] = args.phone_number
    return {
        "data": {
            "type": "profile-subscription-bulk-delete-job",
            "attributes": {
                "profiles": {"data": [{"type": "profile", "attributes": profile_attrs}]}
            },
            "relationships": {"list": {"data": {"type": "list", "id": args.list_id}}},
        }
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Unsubscribe a profile from a list's marketing.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--list-id", dest="list_id", required=True, help="List id")
    parser.add_argument("--email", help="Profile email")
    parser.add_argument("--phone-number", dest="phone_number", help="E.164 phone number")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if not args.email and not args.phone_number:
        parser.error("at least one of --email or --phone-number is required")

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    if not args.yes:
        parser.error("--yes is required to confirm unsubscribe; aborting")

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("profile-subscription-bulk-delete-jobs", json=body)

    check_errors(result)
    print(f"Unsubscribed from list {args.list_id} (job accepted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
