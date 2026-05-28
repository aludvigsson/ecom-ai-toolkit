"""Create or update a Shopify metaobject by (type, handle).

Accepts ``--fields`` as one of:

* A path to a JSON file
* An inline JSON literal (string starting with ``{`` or ``[``)
* ``-`` to read JSON from stdin

The JSON may be either a dict mapping ``key -> value`` (concise form) or
the Shopify-native list of ``{"key": ..., "value": ...}`` objects. The
dict form is normalised before being sent. Honors ``--dry-run`` by
printing the would-be input and exiting 0 without calling the mutation.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from core.config import load_config
from shopify.utils.cli import add_common_flags, configure_logging_from_args, format_output
from shopify.utils.client import ShopifyClient, check_user_errors

_MUTATION = """
mutation MetaobjectUpsert($handle: MetaobjectHandleInput!, $metaobject: MetaobjectUpsertInput!) {
  metaobjectUpsert(handle: $handle, metaobject: $metaobject) {
    metaobject { id handle type fields { key value type } }
    userErrors { field message code }
  }
}
"""


def _read_fields(spec: str) -> Any:
    if spec == "-":
        raw = sys.stdin.read()
    elif spec.startswith("{") or spec.startswith("["):
        raw = spec
    else:
        raw = Path(spec).read_text(encoding="utf-8")
    return json.loads(raw)


def _normalise_fields(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        return [{"key": k, "value": v} for k, v in data.items()]
    if isinstance(data, list):
        return data
    raise ValueError("--fields must be a JSON object (key->value) or array of {key, value} objects")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create or update a Shopify metaobject by (type, handle)."
    )
    add_common_flags(parser)
    parser.add_argument("--type", required=True, help="Metaobject type")
    parser.add_argument("--handle", required=True, help="Metaobject handle")
    parser.add_argument(
        "--fields",
        required=True,
        help="Path to JSON, inline JSON, or '-' for stdin",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    fields = _normalise_fields(_read_fields(args.fields))
    handle_input = {"type": args.type, "handle": args.handle}
    metaobject_input = {"fields": fields}

    if args.dry_run:
        print(format_output({"handle": handle_input, "metaobject": metaobject_input}, args.output))
        return 0

    cfg = load_config(args.config)
    with ShopifyClient(config=cfg) as client:
        data = client.graphql(_MUTATION, {"handle": handle_input, "metaobject": metaobject_input})

    check_user_errors(data, mutation="metaobjectUpsert")
    print(format_output(data["metaobjectUpsert"]["metaobject"], args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
