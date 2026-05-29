"""Activate or deactivate a Klaviyo flow (status change).

High-stakes: --yes is required for live execution. --dry-run works without
--yes and prints the JSON:API PATCH body without calling the API.
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
    return {
        "data": {
            "type": "flow",
            "id": args.id,
            "attributes": {"status": args.status},
        }
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Activate or deactivate a Klaviyo flow.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Flow id")
    parser.add_argument(
        "--status",
        required=True,
        choices=("live", "manual", "draft"),
        help="Target flow status",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    if not args.yes:
        parser.error("--yes is required to confirm a flow status change; aborting")

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.patch(f"flows/{args.id}", json=body)

    check_errors(result)
    resource = result.get("data") or {}
    attrs = resource.get("attributes") or {}
    print(format_output({"id": resource.get("id"), "status": attrs.get("status")}, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
