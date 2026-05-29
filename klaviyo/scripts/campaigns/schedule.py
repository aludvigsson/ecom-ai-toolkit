"""Schedule or immediately send a Klaviyo campaign.

Highest-stakes operation in the domain: --yes is required for live execution.
--dry-run works without --yes and prints the request body without calling the
API. The exact send-job endpoint/shape is verified per-revision in
docs/superpowers/notes/klaviyo-send-endpoint.md (Plan K2 Task 4).

Per that note, scheduling does NOT live on the campaign-send-jobs resource:
the send time is set on the *campaign* via send_strategy.datetime
(PATCH /campaigns/{id}), and the send is then triggered by POST
/campaign-send-jobs with just {type, id}. For an immediate send (--send-now)
no schedule is set on the campaign; only the send job is posted.
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


def _build_campaign_body(args: argparse.Namespace) -> dict | None:
    """Body for PATCH /campaigns/{id} that sets the scheduled send time.

    Returns None for --send-now (no schedule is set on the campaign).
    """
    if args.send_now:
        return None
    return {
        "data": {
            "type": "campaign",
            "id": args.id,
            "attributes": {
                "send_strategy": {
                    "method": "static",
                    "datetime": args.at,
                }
            },
        }
    }


def _build_send_job_body(args: argparse.Namespace) -> dict:
    """Body for POST /campaign-send-jobs that triggers the send."""
    return {
        "data": {
            "type": "campaign-send-job",
            "id": args.id,
        }
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Schedule or send a Klaviyo campaign.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Campaign id")
    parser.add_argument("--at", help="ISO-8601 scheduled send time (required unless --send-now)")
    parser.add_argument(
        "--send-now",
        dest="send_now",
        action="store_true",
        help="Send immediately instead of scheduling",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if not args.send_now and not args.at:
        parser.error("one of --at or --send-now is required")

    campaign_body = _build_campaign_body(args)
    send_job_body = _build_send_job_body(args)

    if args.dry_run:
        print(format_output({"campaign": campaign_body, "send_job": send_job_body}, args.output))
        return 0

    if not args.yes:
        parser.error("--yes is required to confirm scheduling/sending a campaign; aborting")

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        if campaign_body is not None:
            patch_result = client.patch(f"campaigns/{args.id}", json=campaign_body)
            check_errors(patch_result)
        result = client.post("campaign-send-jobs", json=send_job_body)

    check_errors(result)
    when = "now" if args.send_now else args.at
    print(f"Scheduled campaign {args.id} to send {when}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
