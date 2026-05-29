"""Create a Klaviyo email campaign (single-message).

Builds a JSON:API ``campaign`` resource with one email message and one
list/segment audience. --dry-run prints the request body and skips the POST.
Richer multi-message campaigns are deferred to direct API use.
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
    content: dict[str, object] = {
        "subject": args.subject,
        "from_email": args.from_email,
        "from_label": args.from_label,
    }
    if args.preview_text:
        content["preview_text"] = args.preview_text
    message = {
        "type": "campaign-message",
        "attributes": {
            "definition": {
                "channel": args.channel,
                "label": args.name,
                "content": content,
            }
        },
    }
    audiences: dict[str, list[str]] = {"included": [], "excluded": []}
    if args.list_id:
        audiences["included"].append(args.list_id)
    if args.segment_id:
        audiences["included"].append(args.segment_id)
    if args.exclude_id:
        audiences["excluded"].append(args.exclude_id)
    return {
        "data": {
            "type": "campaign",
            "attributes": {
                "name": args.name,
                "audiences": audiences,
                "campaign-messages": {"data": [message]},
            },
        }
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a Klaviyo email campaign.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--name", required=True, help="Campaign name")
    parser.add_argument("--subject", required=True, help="Email subject line")
    parser.add_argument("--from-email", dest="from_email", required=True, help="Sender email")
    parser.add_argument("--from-label", dest="from_label", required=True, help="Sender label")
    parser.add_argument("--preview-text", dest="preview_text", help="Email preview text")
    parser.add_argument("--channel", default="email", help="Message channel (default email)")
    parser.add_argument("--list-id", dest="list_id", help="Included list id")
    parser.add_argument("--segment-id", dest="segment_id", help="Included segment id")
    parser.add_argument("--exclude-id", dest="exclude_id", help="Excluded list/segment id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if not args.list_id and not args.segment_id:
        parser.error("at least one of --list-id or --segment-id is required")

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("campaigns", json=body)

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
