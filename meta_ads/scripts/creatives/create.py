"""Create an ad creative from an existing asset.

POST /act_<id>/adcreatives. Asset *production* is out of scope (spec §2); this
wires an existing page post / link spec into a creative object via
--object-story-spec (a raw JSON string, validated then forwarded unchanged — the
Graph form convention). Not a status-bearing entity, so no PAUSED/gating.
--dry-run prints the node/edge + form and skips the POST.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import json

from core.config import load_config
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, account_path, check_error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create an ad creative from an existing asset/spec."
    )
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument("--name", required=True, help="Creative name")
    parser.add_argument(
        "--object-story-spec",
        dest="object_story_spec",
        required=True,
        help="Object story spec as a JSON string (page post / link spec)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    try:
        json.loads(args.object_story_spec)
    except json.JSONDecodeError as exc:
        parser.error(f"--object-story-spec is not valid JSON: {exc}")

    path = f"{account_path(args.account_id)}/adcreatives"
    data = {"name": args.name, "object_story_spec": args.object_story_spec}

    if args.dry_run:
        print(format_output({"path": path, "data": data}, args.output))
        return 0

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.post(path, data=data)

    check_error(result)
    print(format_output(result, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
