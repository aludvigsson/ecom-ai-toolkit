"""Update a Klaviyo profile by id.

JSON:API update bodies carry the resource id inside ``data``. --dry-run prints
the body and skips the PATCH.
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
    return {"data": {"type": "profile", "id": args.id, "attributes": attributes}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update a Klaviyo profile by id.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Profile id")
    parser.add_argument("--email")
    parser.add_argument("--phone-number", dest="phone_number")
    parser.add_argument("--first-name", dest="first_name")
    parser.add_argument("--last-name", dest="last_name")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.patch(f"profiles/{args.id}", json=body)

    check_errors(result)
    resource = result.get("data") or {}
    attrs = resource.get("attributes") or {}
    print(
        format_output(
            {
                "id": resource.get("id"),
                "email": attrs.get("email"),
                "first_name": attrs.get("first_name"),
                "last_name": attrs.get("last_name"),
            },
            args.output,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
