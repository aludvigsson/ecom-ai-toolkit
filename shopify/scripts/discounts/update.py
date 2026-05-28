"""Update a Shopify discount by ID.

Auto-detects whether the ID belongs to a code or automatic discount and
its specific kind (Basic / Bxgy / FreeShipping) via a dual lookup
(``codeDiscountNode`` + ``automaticDiscountNode``), then dispatches to
the matching ``*Update`` mutation with a partial input built from any
non-None flags.
"""

from __future__ import annotations

import argparse
import sys

from core.config import load_config
from shopify.utils.cli import add_common_flags, configure_logging_from_args, format_output
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

_BASIC_CODE_UPDATE = """
mutation BasicCodeUpdate($id: ID!, $basicCodeDiscount: DiscountCodeBasicInput!) {
  discountCodeBasicUpdate(id: $id, basicCodeDiscount: $basicCodeDiscount) {
    codeDiscountNode { id }
    userErrors { field message code }
  }
}
"""

_BASIC_AUTOMATIC_UPDATE = """
mutation BasicAutoUpdate($id: ID!, $automaticBasicDiscount: DiscountAutomaticBasicInput!) {
  discountAutomaticBasicUpdate(id: $id, automaticBasicDiscount: $automaticBasicDiscount) {
    automaticDiscountNode { id }
    userErrors { field message code }
  }
}
"""

_BXGY_CODE_UPDATE = """
mutation BxgyCodeUpdate($id: ID!, $bxgyCodeDiscount: DiscountCodeBxgyInput!) {
  discountCodeBxgyUpdate(id: $id, bxgyCodeDiscount: $bxgyCodeDiscount) {
    codeDiscountNode { id }
    userErrors { field message code }
  }
}
"""

_BXGY_AUTOMATIC_UPDATE = """
mutation BxgyAutoUpdate($id: ID!, $automaticBxgyDiscount: DiscountAutomaticBxgyInput!) {
  discountAutomaticBxgyUpdate(id: $id, automaticBxgyDiscount: $automaticBxgyDiscount) {
    automaticDiscountNode { id }
    userErrors { field message code }
  }
}
"""

_FREE_SHIPPING_CODE_UPDATE = """
mutation FreeShipCodeUpdate(
  $id: ID!, $freeShippingCodeDiscount: DiscountCodeFreeShippingInput!
) {
  discountCodeFreeShippingUpdate(
    id: $id, freeShippingCodeDiscount: $freeShippingCodeDiscount
  ) {
    codeDiscountNode { id }
    userErrors { field message code }
  }
}
"""

_FREE_SHIPPING_AUTOMATIC_UPDATE = """
mutation FreeShipAutoUpdate(
  $id: ID!, $freeShippingAutomaticDiscount: DiscountAutomaticFreeShippingInput!
) {
  discountAutomaticFreeShippingUpdate(
    id: $id, freeShippingAutomaticDiscount: $freeShippingAutomaticDiscount
  ) {
    automaticDiscountNode { id }
    userErrors { field message code }
  }
}
"""

_DISPATCH: dict[str, tuple[str, str, str]] = {
    "DiscountCodeBasic": (
        "discountCodeBasicUpdate",
        _BASIC_CODE_UPDATE,
        "basicCodeDiscount",
    ),
    "DiscountAutomaticBasic": (
        "discountAutomaticBasicUpdate",
        _BASIC_AUTOMATIC_UPDATE,
        "automaticBasicDiscount",
    ),
    "DiscountCodeBxgy": (
        "discountCodeBxgyUpdate",
        _BXGY_CODE_UPDATE,
        "bxgyCodeDiscount",
    ),
    "DiscountAutomaticBxgy": (
        "discountAutomaticBxgyUpdate",
        _BXGY_AUTOMATIC_UPDATE,
        "automaticBxgyDiscount",
    ),
    "DiscountCodeFreeShipping": (
        "discountCodeFreeShippingUpdate",
        _FREE_SHIPPING_CODE_UPDATE,
        "freeShippingCodeDiscount",
    ),
    "DiscountAutomaticFreeShipping": (
        "discountAutomaticFreeShippingUpdate",
        _FREE_SHIPPING_AUTOMATIC_UPDATE,
        "freeShippingAutomaticDiscount",
    ),
}


def _detect_kind(detect_data: dict) -> str:
    code_node = detect_data.get("codeDiscountNode") or {}
    auto_node = detect_data.get("automaticDiscountNode") or {}
    if code_node:
        return (code_node.get("codeDiscount") or {}).get("__typename") or ""
    if auto_node:
        return (auto_node.get("automaticDiscount") or {}).get("__typename") or ""
    return ""


def _items_selector(applies_to: str) -> dict:
    if applies_to == "all":
        return {"all": True}
    if applies_to.startswith("collection:"):
        return {"collections": {"add": [applies_to.split(":", 1)[1]]}}
    if applies_to.startswith("product:"):
        return {"products": {"productsToAdd": [applies_to.split(":", 1)[1]]}}
    raise ValueError(f"Unknown --applies-to value: {applies_to!r}")


def _value_block(kind: str, value: str) -> dict:
    if kind == "percentage":
        return {"percentage": float(value) / 100.0}
    if kind == "fixed":
        return {"discountAmount": {"amount": value, "appliesOnEachItem": False}}
    raise ValueError(f"_value_block unsupported for kind={kind!r}")


def _build_partial_input(args: argparse.Namespace, *, kind_typename: str) -> dict:
    """Build a partial input — only fields explicitly provided on the CLI."""
    inp: dict = {}
    if args.title is not None:
        inp["title"] = args.title
    if args.code is not None:
        inp["code"] = args.code
    if args.starts_at is not None:
        inp["startsAt"] = args.starts_at
    if args.ends_at is not None:
        inp["endsAt"] = args.ends_at
    if args.usage_limit is not None:
        inp["usageLimit"] = args.usage_limit
    if args.applies_once_per_customer:
        inp["appliesOncePerCustomer"] = True

    # Value updates only make sense on Basic discounts; the user supplies
    # --value plus an implicit kind hint via either --percentage or
    # --fixed-value. Here we keep it simple: --value provided means
    # percentage by default for Basic discounts.
    if args.value is not None and kind_typename in (
        "DiscountCodeBasic",
        "DiscountAutomaticBasic",
    ):
        value_kind = args.value_kind or "percentage"
        inp.setdefault("customerGets", {})["value"] = _value_block(value_kind, args.value)
        if args.applies_to is not None:
            inp["customerGets"]["items"] = _items_selector(args.applies_to)
    return inp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update a Shopify discount.")
    add_common_flags(parser)
    parser.add_argument("--id", required=True, help="Discount node GID")
    parser.add_argument("--title")
    parser.add_argument("--code")
    parser.add_argument("--value")
    parser.add_argument(
        "--value-kind",
        dest="value_kind",
        choices=("percentage", "fixed"),
        help="How to interpret --value when updating a Basic discount",
    )
    parser.add_argument("--starts-at", dest="starts_at")
    parser.add_argument("--ends-at", dest="ends_at")
    parser.add_argument("--applies-to", dest="applies_to")
    parser.add_argument("--usage-limit", dest="usage_limit", type=int)
    parser.add_argument(
        "--applies-once-per-customer",
        dest="applies_once_per_customer",
        action="store_true",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    # Partial customerGets updates need both items + value. Shopify rejects a
    # bare value change with no items selector, so require --applies-to.
    if args.value is not None and args.applies_to is None:
        parser.error("--applies-to is required when changing --value on Basic/Bxgy discounts")

    cfg = load_config(args.config)

    with ShopifyClient(config=cfg) as client:
        detect = client.graphql(_DETECT_QUERY, {"id": args.id})
        kind_typename = _detect_kind(detect)
        if not kind_typename:
            parser.error(f"No discount found for id {args.id!r}")
        if kind_typename not in _DISPATCH:
            parser.error(f"Unsupported discount kind: {kind_typename!r}")

        mutation_name, mutation_text, variable_key = _DISPATCH[kind_typename]
        inp = _build_partial_input(args, kind_typename=kind_typename)

        if args.dry_run:
            print(
                format_output(
                    {
                        "detected_kind": kind_typename,
                        "mutation": mutation_name,
                        "input": inp,
                    },
                    args.output,
                )
            )
            return 0

        data = client.graphql(mutation_text, {"id": args.id, variable_key: inp})

    check_user_errors(data, mutation=mutation_name)
    is_code = kind_typename.startswith("DiscountCode")
    node_key = "codeDiscountNode" if is_code else "automaticDiscountNode"
    node = data[mutation_name][node_key] or {}
    print(
        format_output(
            {"id": node.get("id"), "mutation": mutation_name, "kind": kind_typename},
            args.output,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
