"""Update a Klaviyo list by id. --dry-run prints the body and skips the PATCH."""

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
    parser = argparse.ArgumentParser(description="Update a Klaviyo list by id.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="List id")
    parser.add_argument("--name", required=True, help="New list name")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = {"data": {"type": "list", "id": args.id, "attributes": {"name": args.name}}}

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.patch(f"lists/{args.id}", json=body)

    check_errors(result)
    resource = result.get("data") or {}
    print(
        format_output(
            {"id": resource.get("id"), "name": (resource.get("attributes") or {}).get("name")},
            args.output,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
