"""Remove (hashed) users from a custom audience.

DELETE /<audience_id>/users carrying the same Graph ``payload`` object as a
form/query param (NOT a JSON body — spec note). Identifiers come from --value
(repeatable) or --value-file and are normalized + SHA-256-hashed before
transmission. --dry-run prints the request (hashed) and skips the DELETE.
High-stakes: --yes is required for live execution.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from meta_ads.scripts.audiences._users import (
    load_identifiers,
    payload_param,
    schema_for,
)
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, check_error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Remove hashed users from a custom audience.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Custom audience id")
    parser.add_argument(
        "--kind",
        default="email",
        choices=("email", "phone"),
        help="Identifier kind (selects the SHA-256 schema)",
    )
    parser.add_argument(
        "--value",
        action="append",
        help="An identifier to remove (repeatable)",
    )
    parser.add_argument(
        "--value-file",
        dest="value_file",
        help="File with one identifier per line",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    try:
        identifiers = load_identifiers(args)
    except ValueError as exc:
        parser.error(str(exc))

    schema = schema_for(args.kind)
    payload = payload_param(schema, identifiers)
    path = f"{args.id}/users"
    params = {"payload": payload}

    if args.dry_run:
        print(
            format_output(
                {
                    "method": "DELETE",
                    "path": path,
                    "params": params,
                    "count": len(identifiers),
                },
                args.output,
            )
        )
        return 0

    if not args.yes:
        parser.error("--yes is required to remove users from an audience; aborting")

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.delete(path, params=params)

    check_error(result)
    print(format_output(result, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
