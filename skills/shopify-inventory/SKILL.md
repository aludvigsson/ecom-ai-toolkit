---
name: shopify-inventory
description: Read per-SKU inventory levels across all locations and set on-hand quantities at a specific location via the inventory/ CLI scripts. Use when the user says check stock for SKU, inventory levels, low stock, set inventory at warehouse X, stock count for product, where is SKU X stocked, or inventory adjustment. Honors --output table|json|markdown for levels; set.py honors --dry-run.
---

# shopify-inventory

## When to use

- User wants to **check stock for one or more SKUs**: "what's in stock for ABC-001?", "inventory levels for these SKUs", "where is SKU X stocked?", "show low stock", "stock count for product".
- User wants to **adjust on-hand inventory at a specific location**: "set inventory at Warehouse SE to 12", "mark this SKU as 0 at Berlin", "correct the stock count for X", "inventory adjustment for damaged units".

## When NOT to use

- **Bulk inventory upload from CSV** — not implemented in v0.3. Loop over `levels.py --sku X --sku Y ...` for reads, or call `set.py` per row for writes. A proper bulk variant may land later.
- **Inventory transfer between locations** — out of scope. Use `shopify-plugin:shopify-admin` directly for `inventoryMoveQuantities`.
- **Product / variant queries** (titles, prices, tags, status) — delegate to `shopify-products`.
- **Order-level fulfillment** (which orders consumed this stock?) — delegate to `shopify-orders`.
- Auth not working / "is my shop connected?" — delegate to `shopify-auth`.
- Anything not exposed by `levels.py` / `set.py` (inventoryActivate, inventoryDeactivate, multi-location moves, reservation queries) — use `shopify-plugin:shopify-admin` directly.

## Prerequisites

- `shopify-auth` has been run successfully **OR** `store-config.yaml` and `.env.local` exist at repo root with `SHOPIFY_ADMIN_ACCESS_TOKEN` populated.
- Project deps installed: `uv sync --extra shopify`.

If any script in this skill returns an auth-shaped error, stop and delegate to `shopify-auth`.

## How the scripts split

- **`levels.py` is READ-ONLY.** Per-SKU snapshot across all locations the inventory item is stocked at. Returns one row per (sku, location) with the full quantity breakdown.
- **`set.py` is the canonical adjustment.** Writes the on-hand quantity at a specific location via `inventorySetOnHandQuantities`. Use `--dry-run` first to confirm the resolved inventoryItem ID, location ID, and payload before pulling the trigger.

Shopify distinguishes four quantity names:

- **`available`** — what the storefront treats as sellable.
- **`on_hand`** — what's physically present at the location.
- **`committed`** — reserved for unfulfilled paid orders.
- **`reserved`** — held by in-progress checkouts.

`set.py` adjusts the `on_hand` value; `available` derives from `on_hand - committed - reserved` (roughly — Shopify also subtracts safety stock and incoming).

## Canonical workflows

### 1. Check stock for one SKU

```bash
uv run shopify/scripts/inventory/levels.py --sku ABC-001
```

### 2. Multiple SKUs at once

```bash
uv run shopify/scripts/inventory/levels.py \
  --sku ABC-001 --sku DEF-002 --sku GHI-003
```

### 3. Levels for all SKUs in a CSV

```bash
uv run shopify/scripts/inventory/levels.py --from-csv low_stock_audit.csv
```

CSV must have a `sku` column. Extra columns are ignored.

### 4. Adjust on-hand stock at a specific location (always dry-run first)

```bash
uv run shopify/scripts/inventory/set.py \
  --sku ABC-001 \
  --location-name "Warehouse SE" \
  --quantity 12 \
  --dry-run

# Looks right? Drop --dry-run and pick a real reason:
uv run shopify/scripts/inventory/set.py \
  --sku ABC-001 \
  --location-name "Warehouse SE" \
  --quantity 12 \
  --reason cycle_count_available
```

### 5. Set quantity by `--location-id` (avoids name-matching pitfalls)

```bash
uv run shopify/scripts/inventory/set.py \
  --sku ABC-001 \
  --location-id gid://shopify/Location/12345 \
  --quantity 0 \
  --reason damaged
```

## Common pitfalls

- **SKU resolution uses `productVariants(first: 2)`.** If a SKU is shared by multiple variants (a real possibility in Shopify — SKUs are not unique by default), **both `levels.py` and `set.py` raise `AmbiguousSkuError` and refuse to act**. The fix is to pass the explicit variant via a future `--variant-id` flag (not yet supported in v0.3) or rename one of the duplicates first.
- **`--location-name` matches case-insensitively but requires an EXACT name otherwise** — no substring or fuzzy matching. `"warehouse se"`, `"Warehouse SE"`, and `"WAREHOUSE SE"` all match `"Warehouse SE"` in the shop, but `"Warehouse"` alone does not. If you have multiple locations with the same name (case-insensitive), the script raises `AmbiguousLocationError`; use `--location-id` to disambiguate.
- **`--reason` MUST be one of Shopify's enumerated values.** Free-form text is rejected by the API. Common values: `correction`, `cycle_count_available`, `damaged`, `movement_created`, `movement_updated`, `movement_received`, `movement_canceled`, `other`, `promotion`, `quality_control`, `received`, `reservation_created`, `reservation_deleted`, `reservation_updated`, `restock`, `safety_stock`, `shrinkage`. Default is `correction`.
- **Adjusting `on_hand` does NOT directly change `available` if there are open orders consuming inventory.** If you set on-hand to 12 but you have 3 committed units against unfulfilled orders, `available` will read 9 (give or take safety stock). If you want both to change atomically, use the Shopify Admin UI's "Adjust" workflow, or fall back to the `inventoryAdjustQuantities` mutation via `shopify-plugin:shopify-admin`.
- **Some products have `tracked: false` on their inventoryItem.** Setting on-hand on an untracked item is a no-op (Shopify accepts the mutation but does nothing). **Check the `tracked` column in `levels.py` output first.** If `false`, activate inventory tracking via `shopify-plugin:shopify-admin` (`inventoryItemUpdate` with `tracked: true`) before adjusting.
- **Multi-location stores:** `levels.py` returns up to 50 locations per SKU. If you have more, paginate manually (not yet exposed via flags) — call the Admin API directly via `shopify-plugin:shopify-admin`.
- **One adjustment, one location.** `set.py` writes one `setQuantities` entry per invocation. To set the same SKU at three locations, call it three times. Treat this as a feature, not a bug: each call is a separately attributable adjustment group with its own reason.

## Reference

For `InventorySetOnHandQuantitiesInput`, `InventoryAdjustmentReasonInput`, the full set of inventory mutations (`inventoryAdjustQuantities`, `inventoryMoveQuantities`, `inventoryActivate`, `inventoryDeactivate`, `inventoryItemUpdate`), the `quantities(names: [...])` enum, and pagination semantics on `inventoryLevels`, defer to the `shopify-plugin:shopify-admin` skill from the Shopify-AI-Toolkit plugin dependency.
