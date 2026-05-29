"""Get a single Klaviyo flow by --id.

With --with-actions, also fetches the flow's flow-actions and returns a combined
``{flow, actions}`` object.
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


def _flatten_flow(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "name": attrs.get("name"),
        "status": attrs.get("status"),
        "archived": attrs.get("archived"),
        "trigger_type": attrs.get("trigger_type"),
        "created": attrs.get("created"),
        "updated": attrs.get("updated"),
    }


def _flatten_action(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "action_type": attrs.get("action_type"),
        "status": attrs.get("status"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get a Klaviyo flow by id.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Flow id")
    parser.add_argument(
        "--with-actions",
        dest="with_actions",
        action="store_true",
        help="Also fetch and include the flow's actions",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        body = client.get(f"flows/{args.id}")
        check_errors(body)
        flow = _flatten_flow(body.get("data") or {})
        if args.with_actions:
            actions = [
                _flatten_action(r)
                for r in client.paginate(f"flows/{args.id}/flow-actions", limit=args.limit)
            ]
            print(format_output({"flow": flow, "actions": actions}, args.output))
            return 0

    print(format_output(flow, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
