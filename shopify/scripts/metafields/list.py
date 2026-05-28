"""List Shopify metafields on a specific owner resource.

Shopify's Admin GraphQL has no global ``metafields(...)`` root query — the
metafields connection lives on each owner type (product, variant, collection,
customer, order, shop). This script dispatches to the appropriate root field
based on ``--owner-type``.
"""

from __future__ import annotations

import argparse
import sys

from core.config import load_config
from shopify.utils.cli import add_common_flags, format_output
from shopify.utils.client import ShopifyClient

# field name on the root Query, GraphQL op name, whether owner-id is needed
_OWNERS: dict[str, tuple[str, str, bool]] = {
    "PRODUCT": ("product", "ProductMetafields", True),
    "VARIANT": ("productVariant", "VariantMetafields", True),
    "COLLECTION": ("collection", "CollectionMetafields", True),
    "CUSTOMER": ("customer", "CustomerMetafields", True),
    "ORDER": ("order", "OrderMetafields", True),
    "SHOP": ("shop", "ShopMetafields", False),
}


def _build_query(field: str, op_name: str, needs_id: bool) -> str:
    if needs_id:
        return (
            f"query {op_name}($id: ID!, $first: Int!, $namespace: String, $key: String) {{\n"
            f"  {field}(id: $id) {{\n"
            f"    metafields(first: $first, namespace: $namespace, key: $key) {{\n"
            f"      edges {{ node {{ id namespace key type value }} }}\n"
            f"    }}\n"
            f"  }}\n"
            f"}}\n"
        )
    return (
        f"query {op_name}($first: Int!, $namespace: String, $key: String) {{\n"
        f"  {field} {{\n"
        f"    metafields(first: $first, namespace: $namespace, key: $key) {{\n"
        f"      edges {{ node {{ id namespace key type value }} }}\n"
        f"    }}\n"
        f"  }}\n"
        f"}}\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Shopify metafields on an owner resource.")
    add_common_flags(parser)
    parser.add_argument(
        "--owner-type",
        required=True,
        choices=tuple(_OWNERS.keys()),
        help="Owner resource type",
    )
    parser.add_argument("--owner-id", help="Owner GID (required unless --owner-type SHOP)")
    parser.add_argument("--namespace", help="Filter by metafield namespace")
    parser.add_argument("--key", help="Filter by metafield key")
    args = parser.parse_args(argv)

    field, op_name, needs_id = _OWNERS[args.owner_type]
    if needs_id and not args.owner_id:
        parser.error(f"--owner-id is required when --owner-type is {args.owner_type}")

    cfg = load_config(args.config)
    query = _build_query(field, op_name, needs_id)
    variables: dict = {
        "first": args.limit,
        "namespace": args.namespace,
        "key": args.key,
    }
    if needs_id:
        variables["id"] = args.owner_id

    with ShopifyClient(config=cfg) as client:
        data = client.graphql(query, variables)

    owner_node = data.get(field) or {}
    edges = (owner_node.get("metafields") or {}).get("edges") or []
    rows = [edge["node"] for edge in edges]
    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
