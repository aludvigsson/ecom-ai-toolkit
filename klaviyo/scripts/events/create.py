"""Track a Klaviyo event (POST /events).

Builds a JSON:API ``event`` body referencing a metric (by name) and a profile
(by email). Optional --properties is a JSON object of event properties.
Low-risk; --dry-run prints the body and skips the POST (no --yes gate).
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


def _build_body(args: argparse.Namespace, properties: dict) -> dict:
    profile_attrs: dict[str, object] = {}
    if args.email:
        profile_attrs["email"] = args.email
    if args.phone_number:
        profile_attrs["phone_number"] = args.phone_number
    attributes: dict[str, object] = {
        "metric": {"data": {"type": "metric", "attributes": {"name": args.metric_name}}},
        "profile": {"data": {"type": "profile", "attributes": profile_attrs}},
        "properties": properties,
    }
    if args.value is not None:
        attributes["value"] = args.value
    if args.time:
        attributes["time"] = args.time
    return {"data": {"type": "event", "attributes": attributes}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Track a Klaviyo event.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument(
        "--metric-name", dest="metric_name", required=True, help="Metric name to record"
    )
    parser.add_argument("--email", help="Profile email")
    parser.add_argument("--phone-number", dest="phone_number", help="E.164 phone number")
    parser.add_argument(
        "--properties", help="Event properties as a JSON object string", default="{}"
    )
    parser.add_argument("--value", type=float, help="Numeric event value (e.g. order total)")
    parser.add_argument("--time", help="Event time (ISO-8601); defaults to now server-side")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if not args.email and not args.phone_number:
        parser.error("at least one of --email or --phone-number is required")

    try:
        properties = json.loads(args.properties)
    except json.JSONDecodeError as exc:
        parser.error(f"--properties is not valid JSON: {exc}")

    body = _build_body(args, properties)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("events", json=body)

    check_errors(result)
    print(f"Tracked event {args.metric_name!r} (accepted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
