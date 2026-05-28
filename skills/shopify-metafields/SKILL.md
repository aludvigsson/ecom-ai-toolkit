---
name: shopify-metafields
description: Read, set, and bulk-upsert Shopify metafields and metaobjects via the metafields/ and metaobjects/ CLI scripts. Use when the user says list/set/upsert/delete metafields on products/collections/customers/orders/shop, or manage standalone metaobjects by type and handle. Both single-set and batch (CSV/JSON-stdin) modes supported. Honors --dry-run.
---

# shopify-metafields

Metafields are key-value extensions attached to existing Shopify resources (products, collections, customers, orders, variants, shop). Metaobjects are standalone custom resources defined by a metaobject definition; they have their own `id`, `handle`, and `type` and live independently. Both are managed via this single skill because they're conceptually paired — most custom-data workflows touch both.

## When to use

- User wants to **list metafields** on a resource: "list metafields", "find metafield for product/collection/customer", "show shop-level metafields", "what metafields are on this product".
- User wants to **set a metafield**: "set metafield", "update metafield value", "add a custom field to this product".
- User wants to **bulk-upsert metafields** from JSON: "upsert metafield from batch", "bulk metafield set from JSON", "set 500 metafields at once".
- User wants to **list metaobjects** of a given definition type: "list metaobjects of type X", "show all my custom-content metaobjects".
- User wants to **create or update a metaobject**: "create metaobject", "update metaobject", "upsert metaobject by handle".
- User wants to **delete a metaobject**: "delete metaobject", "remove metaobject by id".

## When NOT to use

- Product / collection / customer / order entity reads or writes → delegate to `shopify-products`, `shopify-collections`, etc.
- Translations on metafields or metaobject field values → delegate to `shopify-translations` (separate skill).
- Metafield **definitions** (the schema, not the values) — not exposed by these scripts. Use `shopify-plugin:shopify-custom-data` directly.
- Auth not working / "is my shop connected?" → delegate to `shopify-auth`.

## Prerequisites

- `shopify-auth` has been run successfully **OR** `store-config.yaml` and `.env.local` exist at repo root with `SHOPIFY_ADMIN_ACCESS_TOKEN` populated.
- Project deps installed: `uv sync --extra shopify`.

If any script in this skill returns an auth-shaped error, stop and delegate to `shopify-auth`.

## Canonical workflows

### 1. List metafields on a product

```bash
uv run shopify/scripts/metafields/list.py \
  --owner-type PRODUCT \
  --owner-id gid://shopify/Product/12345
```

`--owner-type` accepts the standard Shopify owner enums: `PRODUCT`, `PRODUCTVARIANT`, `COLLECTION`, `CUSTOMER`, `ORDER`, `SHOP`, and others. All owner types except `SHOP` require `--owner-id`.

### 2. List shop-level metafields (no owner-id)

```bash
uv run shopify/scripts/metafields/list.py --owner-type SHOP
```

Shop is a singleton, so the script omits `--owner-id` for this owner type.

### 3. Filter by namespace and key

```bash
uv run shopify/scripts/metafields/list.py \
  --owner-type PRODUCT \
  --owner-id gid://shopify/Product/12345 \
  --namespace custom \
  --key color
```

Both filters are optional and combine. Omit `--key` to see all metafields in a namespace.

### 4. Set a single metafield (dry-run, then for real)

```bash
uv run shopify/scripts/metafields/set.py \
  --owner-id gid://shopify/Product/12345 \
  --namespace custom \
  --key color \
  --value blue \
  --type single_line_text_field \
  --dry-run
```

Dry-run prints the `MetafieldsSetInput` payload and exits 0. Once the payload looks right, drop the flag:

```bash
uv run shopify/scripts/metafields/set.py \
  --owner-id gid://shopify/Product/12345 \
  --namespace custom \
  --key color \
  --value blue \
  --type single_line_text_field
```

### 5. Bulk set metafields from stdin JSON

```bash
cat batch.json | uv run shopify/scripts/metafields/set.py --batch -
```

`batch.json` is a JSON list of `MetafieldsSetInput` objects:

```json
[
  { "ownerId": "gid://shopify/Product/1", "namespace": "custom", "key": "color", "value": "blue", "type": "single_line_text_field" },
  { "ownerId": "gid://shopify/Product/2", "namespace": "custom", "key": "color", "value": "red",  "type": "single_line_text_field" }
]
```

The script chunks at 25 metafields per Shopify API call. Batches of 100+ items work fine but issue multiple round trips. Add `--dry-run` to see the chunked payload without writing.

### 6. List metaobjects of a given type

```bash
uv run shopify/scripts/metaobjects/list.py --type my_custom_type --limit 50
```

`--type` is the metaobject definition's `type` field (e.g. `my_custom_type`, `lookbook_entry`). Pagination via `--limit`.

### 7. Upsert a metaobject (dict-form fields, dry-run first)

```bash
uv run shopify/scripts/metaobjects/upsert.py \
  --type my_type \
  --handle my-instance \
  --fields '{"color":"blue","size":"L"}' \
  --dry-run
```

Upsert is keyed on `(type, handle)`: if a metaobject with that pair exists, it's updated; otherwise it's created. Dry-run prints the would-be `MetaobjectUpsertInput`. Drop the flag to execute:

```bash
uv run shopify/scripts/metaobjects/upsert.py \
  --type my_type \
  --handle my-instance \
  --fields '{"color":"blue","size":"L"}'
```

### 8. Upsert a metaobject from a JSON file (list form)

```bash
uv run shopify/scripts/metaobjects/upsert.py \
  --type my_type \
  --handle my-instance \
  --fields fields.json
```

`--fields` accepts either a JSON file path or an inline JSON string. Both dict form `{"key":"value"}` and explicit list form `[{"key":"k","value":"v"}, ...]` are accepted; the script normalises dict form to list form before sending.

### 9. Delete a metaobject

```bash
uv run shopify/scripts/metaobjects/delete.py \
  --id gid://shopify/Metaobject/12345 \
  --dry-run
```

Dry-run works without `--yes` and prints what would be deleted. To actually delete, you must pass `--yes`:

```bash
uv run shopify/scripts/metaobjects/delete.py \
  --id gid://shopify/Metaobject/12345 \
  --yes
```

## Common pitfalls

- **Metafields require a `type` on every set.** Common types: `single_line_text_field`, `multi_line_text_field`, `number_integer`, `number_decimal`, `boolean`, `date`, `date_time`, `color`, `weight`, `dimension`, `volume`, `rating`, `json`, `url`, `money`, `metaobject_reference`, and `list.<type>` for any list variant. Mismatched types are rejected by Shopify with `userErrors`.
- **`metafields/set.py` chunks at 25 per call.** Batches of 100+ work but issue multiple API calls. Plan rate-limit budget accordingly.
- **`SHOP` owner type does NOT take `--owner-id`.** All other owner types (`PRODUCT`, `PRODUCTVARIANT`, `COLLECTION`, `CUSTOMER`, `ORDER`, ...) require it. The script errors early if you pass `--owner-id` with `SHOP` or omit it with anything else.
- **`metaobjects/upsert.py` `--fields` is polymorphic.** Dict form `{"color":"blue"}` is convenient for hand-typed cases; list form `[{"key":"color","value":"blue"}, ...]` is required if any key is not a valid Python identifier or if order matters. The script auto-normalises dict → list before sending.
- **Upsert is keyed on `(type, handle)`.** Passing the same `--type` + `--handle` pair twice updates the same metaobject; it does not create a duplicate. To create a fresh metaobject, pick a new handle.
- **`metaobjects/delete.py` requires `--yes` to execute.** `--dry-run` works without `--yes`, but a real delete needs the explicit confirmation flag. This is intentional — deletes are irreversible.
- **Complex metafield types are stringified JSON.** For `json`, `list.<type>`, `metaobject_reference`, and any reference list, the `--value` must be a JSON-encoded string (e.g. `--value '["a","b"]'` for `list.single_line_text_field`, or `--value 'gid://shopify/Metaobject/1'` for `metaobject_reference`). See the plugin reference below for the full type matrix.

## Reference

For the full Admin GraphQL schema — every supported metafield `type`, the `MetafieldsSetInput` shape, the `MetaobjectUpsertInput` and `MetaobjectField` shapes, owner-type enums, and capabilities outside these five scripts (metafield definitions, metaobject definitions, capabilities, access scopes) — defer to the `shopify-plugin:shopify-custom-data` skill from the Shopify-AI-Toolkit plugin dependency, or `shopify-plugin:shopify-admin` if the custom-data skill isn't available.
