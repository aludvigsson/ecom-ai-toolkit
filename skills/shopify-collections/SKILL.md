---
name: shopify-collections
description: List, create, update, and bulk-populate Shopify collections via the collections/ CLI scripts. Use when the user says list collections, find smart collections, create smart or custom collection, update collection title/handle/sort order, or add products to a collection in bulk (by handle or from CSV). Honors --dry-run, --output table|json|markdown, and the --config override.
---

# shopify-collections

## When to use

- User wants to **list / browse** collections: "list all collections", "find smart collections", "show custom collections only", "search collections by title".
- User wants to **create** a collection: "create a custom collection called Summer 2026", "create a smart collection from rules", "make a sale collection that auto-includes tagged products".
- User wants to **update** a collection: change title, handle, descriptionHtml, sort order, or the smart-collection rule set.
- User wants to **bulk-populate** a custom collection: "add these 500 products to collection X", "add products by handle list", "add products from CSV".

## When NOT to use

- Product-level queries (list, detail, update, bulk price) → delegate to `shopify-products`.
- Reading or writing **metafields** on a collection → delegate to `shopify-metafields` (separate skill).
- Reading or writing **translations** on a collection → delegate to `shopify-translations` (separate skill).
- Auth not working / "is my shop connected?" → delegate to `shopify-auth`.
- Deleting collections, reordering manual-sort positions, or anything not exposed by the four scripts → use `shopify-plugin:shopify-admin` directly.

## Prerequisites

- `shopify-auth` has been run successfully **OR** `store-config.yaml` and `.env.local` exist at repo root with `SHOPIFY_ADMIN_ACCESS_TOKEN` populated.
- Project deps installed: `uv sync --extra shopify`.

If any script in this skill returns an auth-shaped error, stop and delegate to `shopify-auth`.

## Canonical workflows

### 1. List all collections

```bash
uv run shopify/scripts/collections/list.py --limit 100
```

Output formats: `--output table|json|markdown`. Pass `--query` for raw Shopify collection search syntax.

### 2. List smart collections only

```bash
uv run shopify/scripts/collections/list.py --type smart
```

`--type` accepts `smart`, `custom`, or `all` (default). Internally this translates to a `collection_type:smart|custom` clause appended to any `--query` you also pass.

### 3. Create a custom collection (dry-run, then for real)

```bash
uv run shopify/scripts/collections/create.py \
  --title "Summer 2026" \
  --handle summer-2026 \
  --dry-run
```

Dry-run prints the would-be `CollectionInput` and exits 0. Once it looks right, drop the flag:

```bash
uv run shopify/scripts/collections/create.py \
  --title "Summer 2026" \
  --handle summer-2026
```

Other optional flags: `--description-html` (HTML, see pitfall below), `--sort-order` (one of `ALPHA_ASC`, `ALPHA_DESC`, `BEST_SELLING`, `CREATED`, `CREATED_DESC`, `MANUAL`, `PRICE_ASC`, `PRICE_DESC`).

### 4. Create a smart collection from a rules JSON file

```bash
uv run shopify/scripts/collections/create.py \
  --title "Sale" \
  --rules rules.json
```

`rules.json` shape:

```json
{
  "appliedDisjunctively": false,
  "rules": [
    { "column": "TAG", "relation": "EQUALS", "condition": "sale" },
    { "column": "TYPE", "relation": "EQUALS", "condition": "Bedding" }
  ]
}
```

`appliedDisjunctively: false` means AND across rules; `true` means OR. The presence of `--rules` is what makes the collection smart — omit it and you get a custom collection. Defer to `shopify-plugin:shopify-admin` for the full list of valid `column` and `relation` enum values.

### 5. Update a collection's sort order

```bash
uv run shopify/scripts/collections/update.py \
  --id gid://shopify/Collection/12345 \
  --sort-order BEST_SELLING
```

Updatable flags: `--title`, `--handle`, `--description-html`, `--sort-order`, `--rules`. Only the flags you pass are sent — omitted fields aren't blanked. `--dry-run` prints the `CollectionInput` and exits 0.

### 6. Bulk-add products by handle

```bash
uv run shopify/scripts/collections/add_products.py \
  --collection-id gid://shopify/Collection/12345 \
  --handles pearl-classic,fluffy-duvet
```

Handles are resolved to GIDs via `productByHandle` before the mutation. A missing handle raises and aborts the run.

### 7. Bulk-add products from CSV

CSV columns: `product_id` **OR** `handle` (one per row). If both are present on a row, `product_id` wins.

```bash
uv run shopify/scripts/collections/add_products.py \
  --collection-id gid://shopify/Collection/12345 \
  --from-csv products.csv --dry-run
```

Dry-run prints the chunked payload (250 product IDs per chunk) and exits 0. Then run for real:

```bash
uv run shopify/scripts/collections/add_products.py \
  --collection-id gid://shopify/Collection/12345 \
  --from-csv products.csv
```

## Common pitfalls

- **`--description-html` is HTML, not plain text.** Same caveat as `shopify-products`: passing `"Hello & welcome <3"` will render literally. Wrap in `<p>...</p>` and escape `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;` yourself before passing.
- **Dry-run on `add_products.py` skips ALL graphql calls** — including the `productByHandle` lookups. So the printed chunks show the *raw* handle/id values from the CSV, not resolved GIDs. The real run will resolve handles before chunking.
- **`add_products.py` chunks at 250 product IDs per mutation.** For very large lists, run with `--dry-run` first to confirm the chunk count and total size before incurring the API spend.
- **Smart vs custom is decided by `--rules` on `create.py`.** Same script handles both: pass `--rules path/to/rules.json` and you get a smart collection; omit and you get a custom one. There is no separate `--smart` flag.
- **Smart collections cannot have products explicitly added.** They're populated by their rule set. Running `add_products.py` against a smart collection's GID will return a `userErrors` response from `collectionAddProducts` and the script will raise. Convert to a custom collection (or change the rules) first.
- **Handle resolution is one query per handle.** No batching. For thousands of handles, prefer a CSV with pre-resolved `product_id` GIDs — it skips the lookup phase entirely.

## Reference

For full Admin GraphQL schema — `CollectionInput` fields not exposed here, the complete `CollectionSortOrder` enum, all valid `CollectionRuleColumn` / `CollectionRuleRelation` values for smart-collection rules, and resources outside these four scripts (delete, reorder, publication targets) — defer to the `shopify-plugin:shopify-admin` skill from the Shopify-AI-Toolkit plugin dependency.
