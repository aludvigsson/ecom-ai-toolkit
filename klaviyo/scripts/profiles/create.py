"""Create a Klaviyo profile.

Builds a JSON:API ``profile`` resource from the given attributes. --dry-run
prints the request body and skips the POST.
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
    attributes: dict[str, object] = {}
    if args.email:
        attributes["email"] = args.email
    if args.phone_number:
        attributes["phone_number"] = args.phone_number
    if args.first_name:
        attributes["first_name"] = args.first_name
    if args.last_name:
        attributes["last_name"] = args.last_name
    return {"data": {"type": "profile", "attributes": attributes}}


def _flatten(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "email": attrs.get("email"),
        "first_name": attrs.get("first_name"),
        "last_name": attrs.get("last_name"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a Klaviyo profile.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--email", help="Profile email")
    parser.add_argument("--phone-number", dest="phone_number", help="E.164 phone number")
    parser.add_argument("--first-name", dest="first_name")
    parser.add_argument("--last-name", dest="last_name")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if not args.email and not args.phone_number:
        parser.error("at least one of --email or --phone-number is required")

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("profiles", json=body)

    check_errors(result)
    print(format_output(_flatten(result.get("data") or {}), args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
