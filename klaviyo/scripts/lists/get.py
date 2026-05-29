"""Get a Klaviyo list by id, optionally with its member profiles.

--with-members appends a paginated profile listing (capped by --limit) under a
``members`` key in the output.
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


def _flatten_list(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "name": attrs.get("name"),
        "created": attrs.get("created"),
        "updated": attrs.get("updated"),
    }


def _flatten_profile(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "email": attrs.get("email"),
        "first_name": attrs.get("first_name"),
        "last_name": attrs.get("last_name"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get a Klaviyo list by id.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="List id")
    parser.add_argument(
        "--with-members",
        dest="with_members",
        action="store_true",
        help="Also list member profiles (capped by --limit)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        body = client.get(f"lists/{args.id}")
        check_errors(body)
        out = _flatten_list(body.get("data") or {})
        if args.with_members:
            out["members"] = [
                _flatten_profile(r)
                for r in client.paginate(f"lists/{args.id}/profiles", limit=args.limit)
            ]

    print(format_output(out, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
