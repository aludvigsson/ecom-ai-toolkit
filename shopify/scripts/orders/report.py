"""Markdown sales summary for a date range, powered by ShopifyClient.bulk_query.

GMV, refunds, net revenue, top-N SKUs by units sold. Multi-currency aware:
reports the currency code of the first non-cancelled order without converting.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from decimal import Decimal

from core.config import load_config
from shopify.utils.cli import add_common_flags, configure_logging_from_args
from shopify.utils.client import ShopifyClient


def _bulk_op_string(date_from: str, date_to: str) -> str:
    return f"""
{{
  orders(query: "created_at:>={date_from} created_at:<={date_to}") {{
    edges {{ node {{
      id name createdAt cancelledAt
      displayFinancialStatus
      currentTotalPriceSet {{ shopMoney {{ amount currencyCode }} }}
      currentTotalRefundedSet {{ shopMoney {{ amount currencyCode }} }}
      lineItems {{ edges {{ node {{ sku quantity name }} }} }}
    }} }}
  }}
}}
""".strip()


def _money(node: dict | None, key: str) -> tuple[Decimal, str | None]:
    if not node:
        return Decimal("0"), None
    money = (node.get(key) or {}).get("shopMoney") or {}
    raw = money.get("amount")
    amt = Decimal(raw) if raw is not None else Decimal("0")
    return amt, money.get("currencyCode")


def _format_money(amount: Decimal, currency: str | None) -> str:
    formatted = f"{amount:,.2f}"
    return f"{formatted} {currency}" if currency else formatted


def _build_report(
    *,
    date_from: str,
    date_to: str,
    orders_by_id: dict[str, dict],
    lineitems_by_order: dict[str, list[dict]],
    top_n: int,
) -> str:
    gmv = Decimal("0")
    refunds = Decimal("0")
    count = 0
    currency: str | None = None
    sku_units: dict[str, int] = defaultdict(int)
    sku_names: dict[str, str] = {}

    for order_id, order in orders_by_id.items():
        if order.get("cancelledAt"):
            continue
        count += 1
        price, cur = _money(order, "currentTotalPriceSet")
        refund, _ = _money(order, "currentTotalRefundedSet")
        gmv += price
        refunds += refund
        if currency is None and cur is not None:
            currency = cur
        for li in lineitems_by_order.get(order_id, []):
            sku = li.get("sku") or "(no sku)"
            qty = int(li.get("quantity") or 0)
            sku_units[sku] += qty
            if sku not in sku_names and li.get("name"):
                sku_names[sku] = li["name"]

    net = gmv - refunds
    top = sorted(sku_units.items(), key=lambda kv: kv[1], reverse=True)[:top_n]

    lines: list[str] = []
    lines.append(f"# Orders summary {date_from} to {date_to}")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Order count | {count} |")
    lines.append(f"| GMV | {_format_money(gmv, currency)} |")
    lines.append(f"| Refunds | {_format_money(refunds, currency)} |")
    lines.append(f"| Net | {_format_money(net, currency)} |")
    lines.append("")
    lines.append(f"## Top {top_n} SKUs by units sold")
    lines.append("")
    lines.append("| SKU | Units | Product |")
    lines.append("|---|---|---|")
    for sku, units in top:
        lines.append(f"| {sku} | {units} | {sku_names.get(sku, '')} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Markdown sales summary for a date range via Bulk Operations."
    )
    add_common_flags(parser)
    parser.add_argument("--from", dest="date_from", required=True, help="ISO date lower bound")
    parser.add_argument("--to", dest="date_to", required=True, help="ISO date upper bound")
    parser.add_argument("--top-n", dest="top_n", type=int, default=5)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    bulk_query = _bulk_op_string(args.date_from, args.date_to)

    orders_by_id: dict[str, dict] = {}
    lineitems_by_order: dict[str, list[dict]] = defaultdict(list)

    with ShopifyClient(config=cfg) as client:
        for row in client.bulk_query(bulk_query):
            parent = row.get("__parentId")
            if parent is None:
                orders_by_id[row["id"]] = row
            else:
                lineitems_by_order[parent].append(row)

    report = _build_report(
        date_from=args.date_from,
        date_to=args.date_to,
        orders_by_id=orders_by_id,
        lineitems_by_order=dict(lineitems_by_order),
        top_n=args.top_n,
    )
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
