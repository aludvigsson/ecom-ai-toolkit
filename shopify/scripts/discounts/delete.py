"""Delete a Shopify discount by ID.

Detects whether the ID belongs to a code or automatic discount via a
dual lookup (``codeDiscountNode`` + ``automaticDiscountNode``) and
dispatches to ``discountCodeDelete`` or ``discountAutomaticDelete``.

Destructive: requires ``--yes`` for live execution. ``--dry-run`` runs
the detect query (so the operator can see what would be deleted) and
exits 0 without requiring ``--yes``.
"""

from __future__ import annotations

import argparse
import sys

from core.config import load_config
from shopify.utils.cli import add_common_flags
from shopify.utils.client import ShopifyClient, check_user_errors

_DETECT_QUERY = """
query DetectKind($id: ID!) {
  codeDiscountNode(id: $id) {
    codeDiscount { __typename }
  }
  automaticDiscountNode(id: $id) {
    automaticDiscount { __typename }
  }
}
"""

_CODE_DELETE = """
mutation CodeDelete($id: ID!) {
  discountCodeDelete(id: $id) {
    deletedCodeDiscountId
    userErrors { field message code }
  }
}
"""

_AUTOMATIC_DELETE = """
mutation AutomaticDelete($id: ID!) {
  discountAutomaticDelete(id: $id) {
    deletedAutomaticDiscountId
    userErrors { field message code }
  }
}
"""


def _detect_kind(detect_data: dict) -> tuple[str, str]:
    """Return (catalog, typename) where catalog is 'code' or 'automatic'."""
    code_node = detect_data.get("codeDiscountNode") or {}
    auto_node = detect_data.get("automaticDiscountNode") or {}
    if code_node:
        return "code", (code_node.get("codeDiscount") or {}).get("__typename") or ""
    if auto_node:
        return "automatic", (auto_node.get("automaticDiscount") or {}).get("__typename") or ""
    return "", ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Delete a Shopify discount by ID.")
    add_common_flags(parser)
    parser.add_argument("--id", required=True, help="Discount node GID")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm destructive deletion (required for live execution)",
    )
    args = parser.parse_args(argv)

    if not args.dry_run and not args.yes:
        parser.error("--yes is required to confirm deletion; aborting")

    cfg = load_config(args.config)

    with ShopifyClient(config=cfg) as client:
        detect = client.graphql(_DETECT_QUERY, {"id": args.id})
        catalog, typename = _detect_kind(detect)
        if not catalog:
            parser.error(f"No discount found for id {args.id!r}")

        if args.dry_run:
            print(f"Would delete discount {args.id} (detected as {typename})")
            return 0

        if catalog == "code":
            mutation_name = "discountCodeDelete"
            data = client.graphql(_CODE_DELETE, {"id": args.id})
        else:
            mutation_name = "discountAutomaticDelete"
            data = client.graphql(_AUTOMATIC_DELETE, {"id": args.id})

    check_user_errors(data, mutation=mutation_name)
    deleted_key = "deletedCodeDiscountId" if catalog == "code" else "deletedAutomaticDiscountId"
    print(f"Deleted: {data[mutation_name][deleted_key]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
