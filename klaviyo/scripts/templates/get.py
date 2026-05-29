"""Get a Klaviyo email template by id (includes rendered html/text attributes)."""

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


def _flatten(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "name": attrs.get("name"),
        "editor_type": attrs.get("editor_type"),
        "html": attrs.get("html"),
        "text": attrs.get("text"),
        "created": attrs.get("created"),
        "updated": attrs.get("updated"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get a Klaviyo email template by id.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Template id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        body = client.get(f"templates/{args.id}")
        check_errors(body)
        resource = body.get("data") or {}

    print(format_output(_flatten(resource), args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
