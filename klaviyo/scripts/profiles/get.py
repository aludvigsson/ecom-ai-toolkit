"""Get a single Klaviyo profile by --id or by --email.

By email, resolves via a filtered list query and raises ResourceNotFoundError
when no profile matches.
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
from klaviyo.utils.client import KlaviyoClient, ResourceNotFoundError, check_errors


def _flatten(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "email": attrs.get("email"),
        "phone_number": attrs.get("phone_number"),
        "first_name": attrs.get("first_name"),
        "last_name": attrs.get("last_name"),
        "created": attrs.get("created"),
        "updated": attrs.get("updated"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get a Klaviyo profile by id or email.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", help="Profile id")
    parser.add_argument("--email", help="Profile email (resolved to id)")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if not args.id and not args.email:
        parser.error("one of --id or --email is required")

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        if args.id:
            body = client.get(f"profiles/{args.id}")
            check_errors(body)
            resource = body.get("data") or {}
        else:
            body = client.get("profiles", params={"filter": f'equals(email,"{args.email}")'})
            check_errors(body)
            data = body.get("data") or []
            if not data:
                raise ResourceNotFoundError(f"profile with email {args.email!r}")
            resource = data[0]

    print(format_output(_flatten(resource), args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
