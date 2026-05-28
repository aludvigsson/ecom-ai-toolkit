---
name: shopify-products
description: Read, update, and bulk-price-change Shopify products via the products/ CLI scripts. Use when the user says list products, find product by SKU/handle, get product detail, update product title/description/status/tags/vendor, or bulk update prices from a CSV. Honors --dry-run, --output table|json|markdown, and the --config override.
---

# shopify-products

## When to use

- User wants to **list / browse** products: "list active products", "show me draft products", "find products by vendor X", "products tagged sale".
- User wants to **inspect a single product**: "show me product detail for handle pearl-classic", "get product gid://shopify/Product/...", "what variants does this product have?", "show metafields / translations for product X".
- User wants to **update product fields**: title, descriptionHtml, status (ACTIVE/DRAFT/ARCHIVED), tags, vendor.
- User wants to **bulk change variant prices** from a CSV (with optional `compare_at_price`).
- User wants to **resume** a previously interrupted bulk price run.

## When NOT to use

- Auth not working / "is my shop connected?" → delegate to `shopify-auth`.
- The user wants to *create* a brand-new product. These scripts only read and update; creation isn't covered. Use the `shopify-plugin:shopify-admin` skill's `productCreate` mutation.
- The user wants order, customer, collection, or inventory operations. Not in this skill.
- The user wants to update *variant-level* fields other than price (e.g. SKU, barcode, inventory). Not covered here — use `shopify-plugin:shopify-admin`.

## Prerequisites

- `shopify-auth` has been run successfully **OR** `store-config.yaml` and `.env.local` exist at repo root with `SHOPIFY_ADMIN_ACCESS_TOKEN` populated.
- Project deps installed: `uv sync --extra shopify`.

If the user hits any auth-shaped error from a script in this skill, stop and delegate to `shopify-auth`.

## Canonical workflows

### 1. List active products

```bash
uv run shopify/scripts/products/list.py --status ACTIVE --limit 50
```

Other filters: `--vendor "Acme Co"`, `--tag sale`, `--query "title:*pearl*"` (raw Shopify search syntax — wildcards `*` allowed). Output formats: `--output table|json|markdown`.

### 2. Get product detail by handle

```bash
uv run shopify/scripts/products/get.py --handle pearl-classic --output json
```

Returns id, title, status, vendor, productType, tags, up to 100 variants (with their metafields), product metafields, and translations for the locale you pass.

### 3. Get product detail by id, with translations

```bash
uv run shopify/scripts/products/get.py --id gid://shopify/Product/1234567890 --locale sv-SE
```

`--id` and `--handle` are mutually exclusive; exactly one is required.

### 4. Update product status to draft (dry-run first)

```bash
uv run shopify/scripts/products/update.py \
  --id gid://shopify/Product/1234567890 \
  --status DRAFT \
  --dry-run
```

This prints the would-be `ProductInput` and exits 0. Once it looks right, re-run without `--dry-run`:

```bash
uv run shopify/scripts/products/update.py \
  --id gid://shopify/Product/1234567890 \
  --status DRAFT
```

Other updatable flags: `--title`, `--description-html` (HTML, see pitfall below), `--tags "a,b,c"`, `--vendor`. Only the flags you pass are sent — omitted fields aren't blanked.

### 5. Bulk price update from CSV

CSV columns: `variant_id` **OR** `sku` (one of the two per row), `price`, and optional `compare_at_price`.

```bash
uv run shopify/scripts/products/bulk_prices.py --from-csv prices.csv --dry-run
```

Dry-run prints the per-product variant id chunks that would be pushed. Then run without `--dry-run`:

```bash
uv run shopify/scripts/products/bulk_prices.py --from-csv prices.csv
```

State is written to `.state/shopify/bulk_prices_<UTC-timestamp>.json` after each successful chunk.

### 6. Resume a previous bulk run

```bash
uv run shopify/scripts/products/bulk_prices.py \
  --resume .state/shopify/bulk_prices_2026-05-28T120000.json
```

The state file remembers which variant IDs already succeeded and the resolved SKU→variant map, so resuming won't re-charge work or re-do lookups.

## Common pitfalls

- **`--description-html` is HTML, not plain text.** Passing `"Hello & welcome <3"` will render literally — including the `&` and `<3`. If you only have plain text, wrap it (`<p>...</p>`) and escape `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;` yourself before passing. The flag was renamed from `--description` precisely to make this explicit.
- **Ambiguous SKUs are refused.** If a CSV row uses `sku` and that SKU matches more than one variant in the store, `bulk_prices.py` raises `AmbiguousSkuError` and aborts before writing anything. Fix by switching that row to an explicit `variant_id` column value.
- **Missing SKUs raise too.** `SkuNotFoundError` halts the run on the first unresolvable SKU. Clean the CSV (or pre-resolve) before retrying.
- **Vendor/tag values with apostrophes / quotes are auto-escaped** in `list.py` via `escape_search_value`. Wildcards (`*`) only work when you pass them through `--query` raw mode, not via `--vendor`/`--tag`.
- **`--dry-run` on writes always exits 0** after printing the would-be input. Always run dry-run first on `update.py` and `bulk_prices.py` before doing the real thing, especially for prices.
- **Do not delete `.state/shopify/` mid-run.** That's how `bulk_prices.py` knows what's already done. If you do delete it, the next run will re-attempt every row from scratch (idempotent on Shopify's side, but wasteful).
- **`get.py` caps variants at 100.** Products with more variants need a paginated query — escalate to `shopify-plugin:shopify-admin`.

## Reference

For full Admin GraphQL schema, mutation argument shapes, and resources not exposed here (productCreate, variant-level mutations beyond price, metafield writes, etc.), defer to the `shopify-plugin:shopify-admin` skill from the Shopify-AI-Toolkit plugin dependency.
