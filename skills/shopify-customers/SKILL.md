---
name: shopify-customers
description: Read-only customer queries via the customers/list.py CLI script — email lookup, tag filter, account-state filter, and a numberOfOrders post-filter for high-LTV segmentation. Use when the user says list customers, find customer by email, high-LTV customers, tagged VIP customers, customers with more than N orders, lapsed customers, newest customers, or disabled accounts. Honors --output table|json|markdown.
---

# shopify-customers

## When to use

- User wants to **find a specific customer or small set of customers**: "find customer alice@example.com", "list newest customers", "show customers tagged VIP", "who has more than 10 orders", "list disabled accounts".
- User wants a **first-pass LTV segmentation**: "high-LTV customers", "customers with at least N orders", "top spenders". Note: `amountSpent` is exposed for inspection but there is no `--min-spent` flag yet — use `--output json | jq` to slice on that field.

## When NOT to use

- **Orders for a specific customer** → delegate to `shopify-orders` with `--customer-email`. This skill returns the customer record only, not their order history.
- **Customer-specific metafield reads** → delegate to `shopify-metafields --owner-type CUSTOMER`.
- **Customer creation, edits, marketing-consent changes, or segment management** → not in v0.3 scope. Use `shopify-plugin:shopify-admin` directly (`customerCreate`, `customerUpdate`, `customerSmsMarketingConsentUpdate`, `customerEmailMarketingConsentUpdate`).
- **Auth not working / "is my shop connected?"** → delegate to `shopify-auth`.

## Read-only scope

This skill currently provides **READ-ONLY access** to customers via `customers/list.py`. Customer creation, updates, segments, and marketing-consent management are out of scope for v0.3 and are not wrapped by any script here.

## Prerequisites

- `shopify-auth` has been run successfully **OR** `store-config.yaml` and `.env.local` exist at repo root with `SHOPIFY_ADMIN_ACCESS_TOKEN` populated.
- Project deps installed: `uv sync --extra shopify`.

If the script returns an auth-shaped error, stop and delegate to `shopify-auth`.

## Canonical workflows

### 1. List the 10 most recently updated customers

```bash
uv run shopify/scripts/customers/list.py --limit 10
```

Output formats: `--output table|json|markdown`. Default is table.

### 2. Find a customer by email

```bash
uv run shopify/scripts/customers/list.py --email "alice@example.com"
```

### 3. Find VIP-tagged customers

```bash
uv run shopify/scripts/customers/list.py --tag vip --limit 100
```

### 4. High-LTV: customers with at least 10 orders

```bash
uv run shopify/scripts/customers/list.py --min-orders 10 --output json \
  | jq '.[] | {email, total_spent, numberOfOrders}'
```

### 5. Disabled accounts

```bash
uv run shopify/scripts/customers/list.py --state disabled
```

## Common pitfalls

- **`--min-orders` is applied AFTER the Shopify query returns.** Shopify search syntax has no numeric-range operator for `numberOfOrders`, so the script fetches the page and filters in-memory. If you set `--limit 50 --min-orders 10`, Shopify returns 50 customers, then we filter — you may get fewer than 50 results back even if 50+ qualify storewide. Use a larger `--limit` (or paginate manually in a follow-up script) for accurate counts.
- **`--state` values must match Shopify exactly:** `enabled`, `disabled`, `invited`, `declined`. Wrong case → no matches. (The CLI restricts these via `choices`, so wrong values are rejected at parse time — but be aware when constructing the same query through other paths.)
- **Tag values with apostrophes are automatically escaped** (via `escape_search_value`). Tag matching in Shopify search is case-insensitive.
- **`amountSpent` is the customer's lifetime amount in the shop's currency.** Multi-currency stores show the converted-to-shop-currency value, not original order currencies. For currency-of-purchase accuracy, drill into orders via `shopify-orders`.
- **This script returns at most one Shopify page** (`--limit` default 50, hard-cap depends on Shopify's API max for `customers`). For a full customer export, use an `orders/report.py`-style bulk-query approach in a follow-up script — not yet provided in v0.3.

## Reference

For the full `customers(query:)` search syntax (all filterable fields, `OR` / `NOT` operators), the complete `CustomerState` enum, and the `Customer` schema (including `amountSpent`, `numberOfOrders`, `tags`, `defaultAddress`, marketing-consent fields), defer to the `shopify-plugin:shopify-admin` skill from the Shopify-AI-Toolkit plugin dependency.
