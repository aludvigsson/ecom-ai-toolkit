"""Render a Klaviyo email template with a template context.

Context comes from --context (inline JSON string) or --context-file (path to a
JSON file). --dry-run prints the request body and skips the POST.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import json
import sys

from core.config import load_config
from klaviyo.utils.cli import (
    add_common_flags,
    add_klaviyo_flags,
    configure_logging_from_args,
    format_output,
)
from klaviyo.utils.client import KlaviyoClient, check_errors


def _resolve_context(args: argparse.Namespace) -> dict:
    if args.context is not None:
        return json.loads(args.context)
    if args.context_file:
        return json.loads(Path(args.context_file).read_text(encoding="utf-8"))
    return {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a Klaviyo template with context.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Template id")
    parser.add_argument("--context", help="Inline JSON template context")
    parser.add_argument("--context-file", dest="context_file", help="Path to a JSON context file")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    context = _resolve_context(args)
    body = {
        "data": {
            "type": "template",
            "id": args.id,
            "attributes": {"context": context},
        }
    }

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("template-render", json=body)

    check_errors(result)
    attrs = (result.get("data") or {}).get("attributes") or {}
    print(format_output({"html": attrs.get("html"), "text": attrs.get("text")}, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
