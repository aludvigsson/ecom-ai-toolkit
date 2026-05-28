"""Create a Shopify discount (code or automatic, four kinds).

Routes to one of eight mutations based on ``--kind`` plus the
presence/absence of ``--code``:

- ``percentage`` + code   → ``discountCodeBasicCreate``
- ``percentage`` no code  → ``discountAutomaticBasicCreate``
- ``fixed``      + code   → ``discountCodeBasicCreate`` (fixedAmount value)
- ``fixed``      no code  → ``discountAutomaticBasicCreate``
- ``bxgy``       + code   → ``discountCodeBxgyCreate``
- ``bxgy``       no code  → ``discountAutomaticBxgyCreate``
- ``free-shipping`` + code → ``discountCodeFreeShippingCreate``
- ``free-shipping`` no code → ``discountAutomaticFreeShippingCreate``

``--value`` for percentages is supplied 0-100 (e.g. ``20`` for 20%) and
normalised to the API's 0-1 fraction internally. For ``fixed`` it is a
money amount string (e.g. ``10.00``).
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

from core.config import load_config
from shopify.utils.cli import add_common_flags, configure_logging_from_args, format_output
from shopify.utils.client import ShopifyClient, check_user_errors

_BASIC_CODE_CREATE = """
mutation BasicCodeCreate($basicCodeDiscount: DiscountCodeBasicInput!) {
  discountCodeBasicCreate(basicCodeDiscount: $basicCodeDiscount) {
    codeDiscountNode { id }
    userErrors { field message code }
  }
}
"""

_BASIC_AUTOMATIC_CREATE = """
mutation BasicAutoCreate($automaticBasicDiscount: DiscountAutomaticBasicInput!) {
  discountAutomaticBasicCreate(automaticBasicDiscount: $automaticBasicDiscount) {
    automaticDiscountNode { id }
    userErrors { field message code }
  }
}
"""

_BXGY_CODE_CREATE = """
mutation BxgyCodeCreate($bxgyCodeDiscount: DiscountCodeBxgyInput!) {
  discountCodeBxgyCreate(bxgyCodeDiscount: $bxgyCodeDiscount) {
    codeDiscountNode { id }
    userErrors { field message code }
  }
}
"""

_BXGY_AUTOMATIC_CREATE = """
mutation BxgyAutoCreate($automaticBxgyDiscount: DiscountAutomaticBxgyInput!) {
  discountAutomaticBxgyCreate(automaticBxgyDiscount: $automaticBxgyDiscount) {
    automaticDiscountNode { id }
    userErrors { field message code }
  }
}
"""

_FREE_SHIPPING_CODE_CREATE = """
mutation FreeShipCodeCreate($freeShippingCodeDiscount: DiscountCodeFreeShippingInput!) {
  discountCodeFreeShippingCreate(freeShippingCodeDiscount: $freeShippingCodeDiscount) {
    codeDiscountNode { id }
    userErrors { field message code }
  }
}
"""

_FREE_SHIPPING_AUTOMATIC_CREATE = """
mutation FreeShipAutoCreate($freeShippingAutomaticDiscount: DiscountAutomaticFreeShippingInput!) {
  discountAutomaticFreeShippingCreate(
    freeShippingAutomaticDiscount: $freeShippingAutomaticDiscount
  ) {
    automaticDiscountNode { id }
    userErrors { field message code }
  }
}
"""


def _items_selector(applies_to: str) -> dict:
    """Translate --applies-to into a Shopify items selector dict."""
    if applies_to == "all":
        return {"all": True}
    if applies_to.startswith("collection:"):
        gid = applies_to.split(":", 1)[1]
        return {"collections": {"add": [gid]}}
    if applies_to.startswith("product:"):
        gid = applies_to.split(":", 1)[1]
        return {"products": {"productsToAdd": [gid]}}
    raise ValueError(f"Unknown --applies-to value: {applies_to!r}")


def _value_block(kind: str, value: str | None) -> dict:
    if kind == "percentage":
        if value is None:
            raise ValueError("--value is required for --kind percentage")
        return {"percentage": float(value) / 100.0}
    if kind == "fixed":
        if value is None:
            raise ValueError("--value is required for --kind fixed")
        return {"discountAmount": {"amount": value, "appliesOnEachItem": False}}
    raise ValueError(f"_value_block unsupported for kind={kind!r}")


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_basic_input(args: argparse.Namespace, *, is_code: bool) -> dict:
    inp: dict = {
        "title": args.title,
        "startsAt": args.starts_at or _now_iso(),
        "customerSelection": {"all": True},
        "customerGets": {
            "items": _items_selector(args.applies_to),
            "value": _value_block(args.kind, args.value),
        },
    }
    if args.ends_at is not None:
        inp["endsAt"] = args.ends_at
    if is_code:
        inp["code"] = args.code
        if args.usage_limit is not None:
            inp["usageLimit"] = args.usage_limit
        if args.applies_once_per_customer:
            inp["appliesOncePerCustomer"] = True
    return inp


def _build_bxgy_input(args: argparse.Namespace, *, is_code: bool) -> dict:
    # Simple "buy 1 get 1 free with item-level selection".
    inp: dict = {
        "title": args.title,
        "startsAt": args.starts_at or _now_iso(),
        "customerSelection": {"all": True},
        "customerBuys": {
            "items": _items_selector(args.applies_to),
            "value": {"quantity": "1"},
        },
        "customerGets": {
            "items": _items_selector(args.applies_to),
            "value": {
                "discountOnQuantity": {
                    "quantity": str(int(float(args.value))) if args.value else "1",
                    "effect": {"percentage": 1.0},
                }
            },
        },
    }
    if args.ends_at is not None:
        inp["endsAt"] = args.ends_at
    if is_code:
        inp["code"] = args.code
        if args.usage_limit is not None:
            inp["usageLimit"] = args.usage_limit
        if args.applies_once_per_customer:
            inp["appliesOncePerCustomer"] = True
    return inp


def _build_free_shipping_input(args: argparse.Namespace, *, is_code: bool) -> dict:
    inp: dict = {
        "title": args.title,
        "startsAt": args.starts_at or _now_iso(),
        "customerSelection": {"all": True},
        "destination": {"all": True},
    }
    if args.ends_at is not None:
        inp["endsAt"] = args.ends_at
    if is_code:
        inp["code"] = args.code
        if args.usage_limit is not None:
            inp["usageLimit"] = args.usage_limit
        if args.applies_once_per_customer:
            inp["appliesOncePerCustomer"] = True
    return inp


def _route(args: argparse.Namespace) -> tuple[str, str, str, dict]:
    """Return (mutation_name, mutation_text, variable_key, input_dict)."""
    is_code = args.code is not None
    if args.kind in ("percentage", "fixed"):
        inp = _build_basic_input(args, is_code=is_code)
        if is_code:
            return (
                "discountCodeBasicCreate",
                _BASIC_CODE_CREATE,
                "basicCodeDiscount",
                inp,
            )
        return (
            "discountAutomaticBasicCreate",
            _BASIC_AUTOMATIC_CREATE,
            "automaticBasicDiscount",
            inp,
        )
    if args.kind == "bxgy":
        inp = _build_bxgy_input(args, is_code=is_code)
        if is_code:
            return ("discountCodeBxgyCreate", _BXGY_CODE_CREATE, "bxgyCodeDiscount", inp)
        return (
            "discountAutomaticBxgyCreate",
            _BXGY_AUTOMATIC_CREATE,
            "automaticBxgyDiscount",
            inp,
        )
    if args.kind == "free-shipping":
        inp = _build_free_shipping_input(args, is_code=is_code)
        if is_code:
            return (
                "discountCodeFreeShippingCreate",
                _FREE_SHIPPING_CODE_CREATE,
                "freeShippingCodeDiscount",
                inp,
            )
        return (
            "discountAutomaticFreeShippingCreate",
            _FREE_SHIPPING_AUTOMATIC_CREATE,
            "freeShippingAutomaticDiscount",
            inp,
        )
    raise ValueError(f"Unknown --kind {args.kind!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a Shopify discount.")
    add_common_flags(parser)
    parser.add_argument(
        "--kind",
        required=True,
        choices=("percentage", "fixed", "bxgy", "free-shipping"),
    )
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--code",
        help="Coupon code. If omitted, creates an automatic discount.",
    )
    parser.add_argument(
        "--value",
        help="Percentage 0-100 (normalised to 0-1) or fixed amount string",
    )
    parser.add_argument("--starts-at", dest="starts_at", help="ISO datetime; default = now")
    parser.add_argument("--ends-at", dest="ends_at", help="ISO datetime; null = no expiry")
    parser.add_argument(
        "--applies-to",
        dest="applies_to",
        default="all",
        help="all | collection:<gid> | product:<gid>",
    )
    parser.add_argument(
        "--usage-limit",
        dest="usage_limit",
        type=int,
        help="Max redemptions (code discounts only)",
    )
    parser.add_argument(
        "--applies-once-per-customer",
        dest="applies_once_per_customer",
        action="store_true",
        help="One redemption per customer (code discounts only)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    # Validate flag combinations at parse time so users get a clear error
    # instead of a silently-dropped flag or a Shopify userError later.
    if args.kind == "free-shipping" and args.value is not None:
        parser.error("--value is not applicable for --kind free-shipping")
    if args.code is None and args.usage_limit is not None:
        parser.error("--usage-limit applies only to code discounts (requires --code)")
    if args.code is None and args.applies_once_per_customer:
        parser.error("--applies-once-per-customer applies only to code discounts (requires --code)")
    if args.kind in ("percentage", "fixed") and args.value is None:
        parser.error(f"--value is required for --kind {args.kind}")
    if args.kind == "percentage" and args.value is not None:
        try:
            pct = float(args.value)
        except ValueError:
            parser.error("--value must be numeric for --kind percentage")
        if not 0 <= pct <= 100:
            parser.error("--value for --kind percentage must be between 0 and 100")

    cfg = load_config(args.config)
    mutation_name, mutation_text, variable_key, inp = _route(args)
    is_code = args.code is not None

    if args.dry_run:
        print(
            format_output(
                {
                    "mutation": mutation_name,
                    "code_or_automatic": "code" if is_code else "automatic",
                    "input": inp,
                },
                args.output,
            )
        )
        return 0

    with ShopifyClient(config=cfg) as client:
        data = client.graphql(mutation_text, {variable_key: inp})

    check_user_errors(data, mutation=mutation_name)
    node_key = "codeDiscountNode" if is_code else "automaticDiscountNode"
    node = data[mutation_name][node_key] or {}
    print(format_output({"id": node.get("id"), "mutation": mutation_name}, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
