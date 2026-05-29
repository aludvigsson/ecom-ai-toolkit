"""Cancel a scheduled Klaviyo campaign send.

High-stakes: --yes is required for live execution. --dry-run works without
--yes and prints the request body without calling the API. The exact cancel
endpoint/shape is verified per-revision in
docs/superpowers/notes/klaviyo-send-endpoint.md (Plan K2 Task 4).
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
            "type": "campaign-send-job",
            "id": args.id,
            "attributes": {"action": "cancel"},
        }
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cancel a scheduled Klaviyo campaign send.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Campaign id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    if not args.yes:
        parser.error("--yes is required to confirm cancelling a campaign send; aborting")

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.patch(f"campaign-send-jobs/{args.id}", json=body)

    check_errors(result)
    print(f"Cancelled send for campaign {args.id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
