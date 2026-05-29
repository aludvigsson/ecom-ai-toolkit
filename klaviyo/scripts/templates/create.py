"""Create a Klaviyo email template.

HTML comes from --html (inline) or --html-file (path). --dry-run prints the
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


def _resolve_html(args: argparse.Namespace) -> str:
    if args.html is not None:
        return args.html
    return Path(args.html_file).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a Klaviyo email template.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--name", required=True, help="Template name")
    parser.add_argument("--html", help="Inline HTML body")
    parser.add_argument("--html-file", dest="html_file", help="Path to an HTML file")
    parser.add_argument("--text", help="Optional plain-text body")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if not args.html and not args.html_file:
        parser.error("one of --html or --html-file is required")

    attributes: dict[str, object] = {"name": args.name, "html": _resolve_html(args)}
    if args.text:
        attributes["text"] = args.text
    body = {"data": {"type": "template", "attributes": attributes}}

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("templates", json=body)

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
