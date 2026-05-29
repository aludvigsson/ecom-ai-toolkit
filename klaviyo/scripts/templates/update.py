"""Update a Klaviyo email template by id.

JSON:API update bodies carry the resource id inside ``data``. HTML may be
supplied via --html or --html-file. --dry-run prints the body and skips the
PATCH.
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
    attributes: dict[str, object] = {}
    if args.name:
        attributes["name"] = args.name
    if args.html is not None:
        attributes["html"] = args.html
    elif args.html_file:
        attributes["html"] = Path(args.html_file).read_text(encoding="utf-8")
    if args.text:
        attributes["text"] = args.text
    return {"data": {"type": "template", "id": args.id, "attributes": attributes}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update a Klaviyo email template by id.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Template id")
    parser.add_argument("--name", help="New template name")
    parser.add_argument("--html", help="Inline HTML body")
    parser.add_argument("--html-file", dest="html_file", help="Path to an HTML file")
    parser.add_argument("--text", help="Plain-text body")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.patch(f"templates/{args.id}", json=body)

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
