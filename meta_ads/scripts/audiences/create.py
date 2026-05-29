"""Create a custom audience container under an ad account.

POST /act_<id>/customaudiences. Creates the (empty) audience; populate it with
audiences/add_users. --dry-run prints the Graph request (node + form data) and
skips the POST. Not --yes-gated: creating an empty audience is low-risk; the
membership writes (add_users/remove_users) and delete are the gated ops.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, account_path, check_error


def _build_data(args: argparse.Namespace) -> dict:
    data: dict[str, object] = {
        "name": args.name,
        "subtype": args.subtype,
    }
    if args.description:
        data["description"] = args.description
    if args.retention_days is not None:
        data["retention_days"] = args.retention_days
    # Graph requires customer_file_source for customer-file (CUSTOM) audiences.
    if args.subtype == "CUSTOM":
        data["customer_file_source"] = args.customer_file_source
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a custom audience.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument("--name", required=True, help="Audience name")
    parser.add_argument(
        "--subtype",
        default="CUSTOM",
        help="Audience subtype (default CUSTOM; LOOKALIKE has its own script)",
    )
    parser.add_argument("--description", help="Audience description")
    parser.add_argument(
        "--retention-days",
        dest="retention_days",
        type=int,
        help="Membership retention in days",
    )
    parser.add_argument(
        "--customer-file-source",
        dest="customer_file_source",
        default="USER_PROVIDED_ONLY",
        choices=(
            "USER_PROVIDED_ONLY",
            "PARTNER_PROVIDED_ONLY",
            "BOTH_USER_AND_PARTNER_PROVIDED",
        ),
        help="Source of identifiers for CUSTOM audiences (Graph-required)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    path = f"{account_path(args.account_id)}/customaudiences"
    data = _build_data(args)

    if args.dry_run:
        print(format_output({"method": "POST", "path": path, "data": data}, args.output))
        return 0

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.post(path, data=data)

    check_error(result)
    print(format_output({"id": result.get("id"), "name": args.name}, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
