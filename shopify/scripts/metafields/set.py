"""Upsert Shopify metafields via metafieldsSet.

Two input modes:

* Single set via flags: ``--owner-id --namespace --key --value --type``
* Batch via ``--batch <path>`` (or ``--batch -`` for stdin), where the input
  is a JSON array of ``MetafieldsSetInput`` objects.

Inputs are chunked at 25 per call (Shopify's per-mutation cap). Honors
``--dry-run`` by printing per-chunk counts and skipping the mutation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from core.config import load_config
from shopify.utils.cli import add_common_flags, configure_logging_from_args, format_output
from shopify.utils.client import ShopifyClient, check_user_errors

_CHUNK_SIZE = 25

_MUTATION = """
mutation MetafieldsSet($input: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $input) {
    metafields { id namespace key value type }
    userErrors { field message code }
  }
}
"""


def _chunk(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _read_batch(path: str) -> list[dict[str, Any]]:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("--batch input must be a JSON array of MetafieldsSetInput objects")
    return data


def _build_single(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "ownerId": args.owner_id,
        "namespace": args.namespace,
        "key": args.key,
        "value": args.value,
        "type": args.type,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upsert Shopify metafields via metafieldsSet.")
    add_common_flags(parser)
    parser.add_argument("--owner-id", help="Owner GID (single-set mode)")
    parser.add_argument("--namespace", help="Metafield namespace (single-set mode)")
    parser.add_argument("--key", help="Metafield key (single-set mode)")
    parser.add_argument("--value", help="Metafield value (single-set mode)")
    parser.add_argument(
        "--type",
        help="Shopify metafield type (e.g. single_line_text_field, number_integer, json)",
    )
    parser.add_argument(
        "--batch",
        help="Path to JSON array of MetafieldsSetInput objects; use '-' for stdin",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    single_flags = (args.owner_id, args.namespace, args.key, args.value, args.type)
    has_any_single = any(f is not None for f in single_flags)
    has_all_single = all(f is not None for f in single_flags)

    if args.batch and has_any_single:
        parser.error("--batch is mutually exclusive with single-set flags")
    if not args.batch and not has_any_single:
        parser.error(
            "either --batch or all single-set flags "
            "(--owner-id --namespace --key --value --type) are required"
        )
    if not args.batch and not has_all_single:
        parser.error(
            "single-set mode requires all of --owner-id, --namespace, --key, --value, --type"
        )

    inputs: list[dict[str, Any]] = _read_batch(args.batch) if args.batch else [_build_single(args)]
    chunks = _chunk(inputs, _CHUNK_SIZE)

    if args.dry_run:
        summary = [{"chunk": i, "count": len(c)} for i, c in enumerate(chunks)]
        print(format_output(summary, args.output))
        return 0

    cfg = load_config(args.config)
    results: list[dict[str, Any]] = []

    with ShopifyClient(config=cfg) as client:
        for chunk in chunks:
            data = client.graphql(_MUTATION, {"input": chunk})
            check_user_errors(data, mutation="metafieldsSet")
            results.extend(data["metafieldsSet"]["metafields"])

    print(format_output(results, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
