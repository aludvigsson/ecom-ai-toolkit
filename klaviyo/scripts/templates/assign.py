"""Assign a template to a Klaviyo campaign message.

Wires an existing template to a campaign's message. --dry-run prints the
request body and skips the POST.
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assign a template to a campaign message.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument(
        "--message-id", dest="message_id", required=True, help="Campaign message id"
    )
    parser.add_argument("--template-id", dest="template_id", required=True, help="Template id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = {
        "data": {
            "type": "campaign-message",
            "id": args.message_id,
            "relationships": {"template": {"data": {"type": "template", "id": args.template_id}}},
        }
    }

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("campaign-message-assign-template", json=body)

    check_errors(result)
    print(f"Assigned template {args.template_id} to message {args.message_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
