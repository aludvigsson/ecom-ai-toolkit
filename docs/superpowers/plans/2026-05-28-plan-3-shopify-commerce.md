# Plan 3: Shopify Commerce Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the commerce half of the Shopify seed: orders, customers, inventory, discounts.

**Architecture:** Same as Plan 2. All scripts use `core.config.load_config()` + `ShopifyClient`, follow conventions in spec § 6.2, share `shopify/utils/cli.py` and `shopify/utils/csv_io.py` (built in Plan 2 — if Plan 2 hasn't run, do Task 0 of Plan 2 first or copy those helpers).

**Tech Stack:** Same as Plan 1. No new top-level deps.

**Spec reference:** §§ 6.1 (orders, customers, inventory, discounts subdirectories), 6.2, 6.6.

**Depends on:** Plan 1 (foundations) and ideally Plan 2 (for shared CLI helpers). If running before Plan 2, lift `shopify/utils/cli.py` + `shopify/utils/csv_io.py` from Plan 2 Task 0 first.

---

## File Structure

| Path | Responsibility |
|---|---|
| `shopify/scripts/orders/list.py` | List orders with date range + status filters |
| `shopify/scripts/orders/report.py` | Markdown summary: count, GMV, refunds, top SKUs |
| `shopify/scripts/customers/list.py` | List customers with filters |
| `shopify/scripts/inventory/levels.py` | Get inventory levels per SKU across locations |
| `shopify/scripts/inventory/set.py` | Set inventory at a specific location |
| `shopify/scripts/discounts/list.py` | List discount codes / automatic discounts |
| `shopify/scripts/discounts/create.py` | Create percentage / fixed / BXGY discount |
| `shopify/scripts/discounts/update.py` | Update an existing discount |
| `shopify/scripts/discounts/delete.py` | Delete a discount |
| `skills/shopify-orders/SKILL.md` | Wraps `orders/*` |
| `skills/shopify-customers/SKILL.md` | Wraps `customers/*` |
| `skills/shopify-inventory/SKILL.md` | Wraps `inventory/*` |
| `skills/shopify-discounts/SKILL.md` | Wraps `discounts/*` |
| `tests/shopify/scripts/test_orders_*.py`, etc. | One test module per script |

---

## Task 1: `shopify/scripts/orders/list.py`

**Files:**
- Create: `shopify/scripts/orders/__init__.py`
- Create: `shopify/scripts/orders/list.py`
- Create: `tests/shopify/scripts/test_orders_list.py`

GraphQL:
```graphql
query Orders($first: Int!, $query: String) {
  orders(first: $first, query: $query, sortKey: CREATED_AT, reverse: true) {
    edges { node {
      id name createdAt
      displayFinancialStatus displayFulfillmentStatus
      currentTotalPriceSet { shopMoney { amount currencyCode } }
      customer { id email displayName }
    } }
    pageInfo { hasNextPage endCursor }
  }
}
```

- [ ] **Step 1: Test (mocked):** verify date-range filter becomes `created_at:>=<from> created_at:<=<to>` in the query string; financial/fulfillment filters become `financial_status:paid fulfillment_status:fulfilled`.
- [ ] **Step 2: Implement.** Flags: `--from <ISO date>`, `--to <ISO date>`, `--financial`, `--fulfillment`, `--customer-email`, plus common flags.
- [ ] **Step 3: Commit**

```bash
mkdir -p shopify/scripts/orders
touch shopify/scripts/orders/__init__.py
# write files; pytest; ruff; commit
git add shopify/scripts/orders/ tests/shopify/scripts/test_orders_list.py
git commit -m "feat(shopify): orders/list.py with date and status filters"
```

---

## Task 2: `shopify/scripts/orders/report.py`

Produces a markdown summary for a date range. Reads via `bulk_query` for large ranges (Plan 1's `ShopifyClient.bulk_query` — if not yet implemented, add to ShopifyClient as part of this task).

- [ ] **Step 0 (if needed): Add `bulk_query` to `ShopifyClient`.** If `ShopifyClient.bulk_query` doesn't exist yet, implement it per spec § 6.5:
  - POST a `bulkOperationRunQuery(query:)` mutation.
  - Poll `currentBulkOperation { status url }` until `COMPLETED` or `FAILED`.
  - Download the JSONL `url` and yield parsed objects.

  Cover with `tests/shopify/test_client.py` cases: `test_bulk_query_polls_and_returns_jsonl`, `test_bulk_query_raises_on_failed_status`.

- [ ] **Step 1: Test (mocked):** small dataset, verify report includes GMV, order count, refund total, top 5 SKUs by units sold.
- [ ] **Step 2: Implement.** Flags: `--from`, `--to` (both required), `--top-n` (default 5). Default output: markdown to stdout.
- [ ] **Step 3: Commit**

```bash
git add shopify/scripts/orders/report.py shopify/utils/client.py tests/shopify/
git commit -m "feat(shopify): orders/report.py + bulk_query support"
```

---

## Task 3: `skills/shopify-orders/SKILL.md`

Triggers: "list recent orders", "monthly sales report", "refund summary", "GMV for date range", "top SKUs last month". Document both `list.py` (drill-in) and `report.py` (summary).

- [ ] Write + commit.

---

## Task 4: `shopify/scripts/customers/list.py`

GraphQL:
```graphql
query Customers($first: Int!, $query: String) {
  customers(first: $first, query: $query, sortKey: UPDATED_AT, reverse: true) {
    edges { node {
      id email displayName createdAt updatedAt
      numberOfOrders amountSpent { amount currencyCode }
      tags state
    } }
    pageInfo { hasNextPage endCursor }
  }
}
```

- [ ] **Step 1: Test (mocked):** verify query filters compose correctly.
- [ ] **Step 2: Implement.** Flags: `--email`, `--tag`, `--state` (enabled/disabled/invited/declined), `--min-orders <n>` (filters in-memory after fetch), plus common.
- [ ] **Step 3: Commit**

---

## Task 5: `skills/shopify-customers/SKILL.md`

Triggers: "list customers", "find customer by email", "high-LTV customers", "tagged customers". v1 is read-only.

- [ ] Write + commit.

---

## Task 6: `shopify/scripts/inventory/levels.py`

Two queries — variant by SKU then `inventoryItem.inventoryLevels` across locations.

```graphql
query LevelsForSku($sku: String!) {
  productVariants(first: 1, query: $sku) {
    edges { node {
      id sku
      inventoryItem {
        id tracked
        inventoryLevels(first: 25) {
          edges { node { available location { id name } } }
        }
      }
    } }
  }
}
```

- [ ] **Step 1: Test (mocked):** verify SKU input is escaped (`sku:'<value>'`) and missing SKU surfaces a clear error.
- [ ] **Step 2: Implement.** Flags: `--sku` (repeatable), or `--from-csv <path>` with a `sku` column.
- [ ] **Step 3: Commit**

---

## Task 7: `shopify/scripts/inventory/set.py`

Uses `inventorySetOnHandQuantities(input: InventorySetOnHandQuantitiesInput!)`.

- [ ] **Step 1: Test (mocked):** verify dry-run prints input and exits 0; non-dry-run posts the mutation and reports the new quantity.
- [ ] **Step 2: Implement.** Flags: `--sku`, `--location-id` (or `--location-name` resolved via locations lookup), `--quantity` (required), `--reason` (passed to mutation), `--dry-run`.
- [ ] **Step 3: Commit**

```graphql
mutation Set($input: InventorySetOnHandQuantitiesInput!) {
  inventorySetOnHandQuantities(input: $input) {
    inventoryAdjustmentGroup { reason changes { name delta } }
    userErrors { field message code }
  }
}
```

---

## Task 8: `skills/shopify-inventory/SKILL.md`

Triggers: "check stock for SKU", "set inventory at Warehouse X", "low stock report" (low stock can re-use `levels.py` with post-filter). Document the `--dry-run` discipline for write ops.

- [ ] Write + commit.

---

## Task 9: `shopify/scripts/discounts/list.py`

GraphQL — `codeDiscountNodes` and `automaticDiscountNodes`:
```graphql
query Codes($first: Int!) {
  codeDiscountNodes(first: $first) {
    edges { node { id codeDiscount { __typename ... on DiscountCodeBasic { title status startsAt endsAt summary codes(first: 1) { edges { node { code } } } } } } }
  }
}
```
(Plus a parallel automatic-discounts query.)

- [ ] **Step 1: Test (mocked).**
- [ ] **Step 2: Implement.** Flags: `--type` (code/automatic/all), `--status` (ACTIVE/EXPIRED/SCHEDULED), plus common.
- [ ] **Step 3: Commit**

---

## Task 10: `shopify/scripts/discounts/create.py`

One of: `discountCodeBasicCreate`, `discountCodeBxgyCreate`, `discountCodeFreeShippingCreate`, `discountAutomaticBasicCreate`. Pick the right mutation based on `--kind`.

- [ ] **Step 1: Test (mocked):** verify percentage vs fixed-amount vs BXGY routes to the correct mutation.
- [ ] **Step 2: Implement.** Flags: `--kind {percentage,fixed,bxgy,free-shipping}`, `--code` (for code-type), `--value` (percent or amount), `--starts-at`, `--ends-at`, `--applies-to {all,collection:<id>,product:<id>}`, `--usage-limit`.
- [ ] **Step 3: Commit**

Example mutation:
```graphql
mutation Basic($input: DiscountCodeBasicInput!) {
  discountCodeBasicCreate(basicCodeDiscount: $input) {
    codeDiscountNode { id }
    userErrors { field message }
  }
}
```

---

## Task 11: `shopify/scripts/discounts/update.py`

Routes to `discountCode*Update` mutations matching the kind of the existing discount. Pre-flight: fetch the discount node, detect type, dispatch.

- [ ] **Step 1: Test (mocked).**
- [ ] **Step 2: Implement.** Flags: `--id` (required), then any of the create flags to override.
- [ ] **Step 3: Commit**

---

## Task 12: `shopify/scripts/discounts/delete.py`

`discountCodeDelete(id: ID!)` or `discountAutomaticDelete(id: ID!)` based on prefix.

- [ ] **Step 1: Test (mocked).**
- [ ] **Step 2: Implement.** Flag: `--id`. Requires `--yes` to confirm (no implicit destructive action).
- [ ] **Step 3: Commit**

---

## Task 13: `skills/shopify-discounts/SKILL.md`

Triggers: "create 20% off code", "list active discount codes", "delete discount FALL2025". Document the four discount kinds (percentage / fixed / BXGY / free shipping) and how to apply scoping (whole order vs collection vs product).

- [ ] Write + commit.

---

## Task 14: Smoke + final sweep

- [ ] Run full test suite: `uv run pytest -v`.
- [ ] Ruff clean.
- [ ] Against a dev shop, run each `list.py` with `--limit 1`.
- [ ] CHANGELOG: add commerce items under `0.3.0`.
- [ ] Tag: `git tag -a v0.3.0-alpha -m "Shopify commerce"`.

---

## Definition of Done

- [ ] 9 scripts under `shopify/scripts/{orders,customers,inventory,discounts}/` implemented and tested.
- [ ] 4 skills (`shopify-orders`, `shopify-customers`, `shopify-inventory`, `shopify-discounts`) written.
- [ ] `ShopifyClient.bulk_query` shipped (Task 2 Step 0) if not already from Plan 2.
- [ ] CI green.
- [ ] CHANGELOG bumped.
