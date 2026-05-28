---
name: shopify-orders
description: List Shopify orders with date/status/customer filters and produce GMV/refunds/top-SKUs markdown reports via the orders/ CLI scripts. Use when the user says list recent orders, monthly sales report, find orders from customer X, GMV for date range, top SKUs last month, or any order drill-in. Honors --output table|json|markdown for list; report is always markdown.
---

# shopify-orders

## When to use

- User wants to **drill into specific orders**: "list recent orders", "find orders from last week", "show orders from customer alice@example.com", "orders from May 2026", "paid + unfulfilled orders right now".
- User wants an **aggregate sales report** over a date range: "GMV last month", "monthly sales report", "refund summary for Q1", "top SKUs last month", "net revenue for May 2026".
- Two-script rule of thumb: `list.py` is for drill-in (find specific orders, see individual details, filter by status/customer). `report.py` is for aggregation (GMV, refunds, net, top SKUs over a range). When in doubt, run `list.py` first to confirm the date range has orders, then `report.py` for the aggregate. `report.py` uses Shopify's Bulk Operations API so unbounded ranges work without manual pagination.

## When NOT to use

- Cancelling or refunding orders → `shopify-order-actions` (future, not yet planned). Use `shopify-plugin:shopify-admin` directly until then.
- Inventory queries on the products in an order → delegate to `shopify-inventory`.
- Customer-side queries (list customers, find by tag, lifetime value) → delegate to `shopify-customers`.
- Auth not working / "is my shop connected?" → delegate to `shopify-auth`.
- Anything not exposed by `list.py` / `report.py` (line-item edits, fulfillment creation, transactions, risk analysis) → use `shopify-plugin:shopify-admin` directly.

## Prerequisites

- `shopify-auth` has been run successfully **OR** `store-config.yaml` and `.env.local` exist at repo root with `SHOPIFY_ADMIN_ACCESS_TOKEN` populated.
- Project deps installed: `uv sync --extra shopify`.

If any script in this skill returns an auth-shaped error, stop and delegate to `shopify-auth`.

## Canonical workflows

### 1. List the 10 most recent orders

```bash
uv run shopify/scripts/orders/list.py --limit 10
```

Output formats: `--output table|json|markdown`. Default is table.

### 2. Orders from a specific date range, paid only

```bash
uv run shopify/scripts/orders/list.py \
  --from 2026-05-01 --to 2026-05-31 \
  --financial paid
```

### 3. Find orders from a customer email

```bash
uv run shopify/scripts/orders/list.py \
  --customer-email "alice@example.com"
```

Email values are escaped before being injected into the Shopify search query.

### 4. Unfulfilled paid orders right now

```bash
uv run shopify/scripts/orders/list.py \
  --financial paid --fulfillment unfulfilled
```

### 5. Monthly sales summary

```bash
uv run shopify/scripts/orders/report.py \
  --from 2026-05-01 --to 2026-05-31
```

Prints a markdown report with order count, GMV, refunds, net, and top 5 SKUs by units sold.

### 6. Top 10 SKUs over a quarter

```bash
uv run shopify/scripts/orders/report.py \
  --from 2026-01-01 --to 2026-03-31 \
  --top-n 10
```

### 7. JSON output for piping to jq

```bash
uv run shopify/scripts/orders/list.py \
  --from 2026-05-01 --to 2026-05-31 \
  --output json | jq '.[] | .id'
```

`report.py` is always markdown — `--output` from the common flags is ignored for the report itself.

## Common pitfalls

- **Dates use ISO `YYYY-MM-DD` and both bounds are inclusive.** `--from` becomes `created_at:>=` and `--to` becomes `created_at:<=`. To get "May 2026", use `--from 2026-05-01 --to 2026-05-31`. There is no implicit timezone — Shopify interprets bare ISO dates in the shop's timezone.
- **`--financial` values are Shopify-internal lowercase strings:** `pending`, `authorized`, `partially_paid`, `paid`, `partially_refunded`, `refunded`, `voided`. Capitalized variants (e.g. `PAID`) silently match nothing.
- **`--fulfillment` values:** `fulfilled`, `partial`, `unfulfilled`, `scheduled`, `on_hold`. Same lowercase rule.
- **`report.py` uses Shopify's Bulk Operations API**, which queues a server-side export. The client blocks while polling. Typical month-of-orders ranges complete in 10–30s; busy stores over multi-month ranges can take 1–2 minutes.
- **Only one bulk operation can run at a time per shop.** If `report.py` errors with "bulk operation already running", either wait for the previous one to finish or cancel it via `bulkOperationCancel` (use `shopify-plugin:shopify-admin`).
- **`report.py` excludes cancelled orders from the count and GMV, but their refunds are still counted** (refunds live on the order regardless of cancellation). To get gross GMV including cancelled orders, modify the script's `if order.get("cancelledAt"): continue` guard or aggregate `list.py --output json` manually.
- **Multi-currency stores:** `report.py` reports the currency of the **first non-cancelled order** seen in the range and does not convert. If your range spans presentments in multiple currencies the displayed code may not match every row. Run separately per Shopify Market when this matters.

## Reference

For the full `orders(query:)` search syntax (all filterable fields, `OR` / `NOT` operators), the complete `OrderFinancialStatus` and `OrderFulfillmentStatus` enums, and the `bulkOperationRunQuery` / `currentBulkOperation` semantics behind `report.py`, defer to the `shopify-plugin:shopify-admin` skill from the Shopify-AI-Toolkit plugin dependency.
