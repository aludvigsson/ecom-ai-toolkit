# Plan 2: Shopify Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the catalog half of the Shopify seed: products, collections, metafields, metaobjects, translations — both scripts and skills.

**Architecture:** Every script reads `store-config.yaml` via `core.config.load_config()`, instantiates `ShopifyClient`, calls Admin GraphQL, prints results. All scripts honor the conventions in spec § 6.2 (`--market`, `--dry-run`, `--output`, `--limit`, `--verbose`). Skills wrap script clusters and reference `shopify-plugin:shopify-admin` for schema deep dives.

**Tech Stack:** Same as Plan 1 (Python 3.12, uv, httpx, pydantic). No new top-level deps.

**Spec reference:** §§ 6.1 (products, collections, metafields, metaobjects, translations subdirectories), 6.2, 6.5, 6.6.

**Depends on:** Plan 1 complete. `ShopifyClient.graphql()` works against a real dev shop.

---

## File Structure

| Path | Responsibility |
|---|---|
| `shopify/scripts/products/list.py` | List products with status/vendor/tag/query filters |
| `shopify/scripts/products/get.py` | Deep read of one product (variants + metafields + translations) |
| `shopify/scripts/products/update.py` | Update title/description/status/tags/vendor |
| `shopify/scripts/products/bulk_prices.py` | CSV → `productVariantsBulkUpdate`; state file in `.state/shopify/` |
| `shopify/scripts/collection/list.py` | List collections (smart and custom) |
| `shopify/scripts/collection/create.py` | Create a custom or smart collection |
| `shopify/scripts/collection/update.py` | Update a collection's title/rules/SEO |
| `shopify/scripts/collection/add_products.py` | Bulk add products to a custom collection |
| `shopify/scripts/metafields/list.py` | List metafields on a resource |
| `shopify/scripts/metafields/set.py` | Upsert metafields (CLI or stdin JSON batch) |
| `shopify/scripts/metaobjects/list.py` | List metaobjects by type |
| `shopify/scripts/metaobjects/upsert.py` | Create or update a metaobject |
| `shopify/scripts/metaobjects/delete.py` | Delete a metaobject |
| `shopify/scripts/translations/list.py` | List translations for a resource + locale |
| `shopify/scripts/translations/register.py` | `translationsRegister` mutation from JSON/CSV |
| `skills/shopify-products/SKILL.md` | Wraps `products/*` |
| `skills/shopify-collections/SKILL.md` | Wraps `collections/*` |
| `skills/shopify-metafields/SKILL.md` | Wraps `metafields/*` + `metaobjects/*` |
| `skills/shopify-translations/SKILL.md` | Wraps `translations/*` |
| `shopify/utils/cli.py` | Shared argparse helpers (`add_common_flags`, output formatting) |
| `shopify/utils/csv_io.py` | Shared CSV read helpers used by bulk scripts |
| `tests/shopify/scripts/test_products_*.py`, etc. | One test module per script cluster |

---

## Task 0: Shared CLI + CSV helpers (do this first)

**Files:**
- Create: `shopify/utils/cli.py`
- Create: `shopify/utils/csv_io.py`
- Create: `tests/shopify/utils/test_cli.py`
- Create: `tests/shopify/utils/test_csv_io.py`

- [ ] **Step 1: Write failing tests**

`tests/shopify/utils/test_cli.py`:
```python
import argparse

from shopify.utils.cli import add_common_flags, format_output


def test_add_common_flags_adds_all_expected():
    parser = argparse.ArgumentParser()
    add_common_flags(parser)
    ns = parser.parse_args(["--market", "se", "--dry-run", "--output", "json", "--limit", "10"])
    assert ns.market == "se"
    assert ns.dry_run is True
    assert ns.output == "json"
    assert ns.limit == 10


def test_format_output_json():
    out = format_output({"a": 1}, "json")
    assert '"a": 1' in out


def test_format_output_table_lists():
    out = format_output([{"id": 1, "name": "x"}, {"id": 2, "name": "y"}], "table")
    assert "id" in out and "name" in out
    assert "x" in out and "y" in out
```

`tests/shopify/utils/test_csv_io.py`:
```python
from shopify.utils.csv_io import read_csv_dicts


def test_read_csv_dicts(tmp_path):
    p = tmp_path / "data.csv"
    p.write_text("sku,price\nABC,99.00\nDEF,49.50\n")
    rows = list(read_csv_dicts(p))
    assert rows == [{"sku": "ABC", "price": "99.00"}, {"sku": "DEF", "price": "49.50"}]
```

- [ ] **Step 2: Confirm tests fail**

```bash
mkdir -p tests/shopify/utils
touch tests/shopify/utils/__init__.py
uv run pytest tests/shopify/utils -v
```
Expected: ImportError.

- [ ] **Step 3: Implement helpers**

`shopify/utils/cli.py`:
```python
"""Shared argparse + output helpers for shopify/scripts/."""
from __future__ import annotations

import argparse
import json


def add_common_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--market", help="Market code from store-config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Skip writes; exercise read path")
    parser.add_argument("--output", choices=("table", "json", "markdown"), default="table")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--config", default="store-config.yaml")
    parser.add_argument("--verbose", action="store_true")


def format_output(data, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(data, indent=2, default=str)
    if fmt == "markdown":
        return _markdown_table(data) if isinstance(data, list) else f"```json\n{json.dumps(data, indent=2)}\n```"
    return _plain_table(data) if isinstance(data, list) else json.dumps(data, indent=2, default=str)


def _plain_table(rows: list[dict]) -> str:
    if not rows:
        return "(no rows)"
    cols = list(rows[0].keys())
    widths = {c: max(len(c), max((len(str(r.get(c, ""))) for r in rows), default=0)) for c in cols}
    header = " | ".join(c.ljust(widths[c]) for c in cols)
    sep = "-+-".join("-" * widths[c] for c in cols)
    body = "\n".join(" | ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols) for r in rows)
    return f"{header}\n{sep}\n{body}"


def _markdown_table(rows: list[dict]) -> str:
    if not rows:
        return "_(no rows)_"
    cols = list(rows[0].keys())
    head = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    body = "\n".join("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |" for r in rows)
    return f"{head}\n{sep}\n{body}"
```

`shopify/utils/csv_io.py`:
```python
"""Shared CSV helpers."""
from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path


def read_csv_dicts(path: str | Path) -> Iterator[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)
```

- [ ] **Step 4: Confirm tests pass**

```bash
uv run pytest tests/shopify/utils -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add shopify/utils/cli.py shopify/utils/csv_io.py tests/shopify/utils/
git commit -m "feat(shopify): shared CLI + CSV helpers for scripts"
```

---

## Task 1: `shopify/scripts/products/list.py`

**Files:**
- Create: `shopify/scripts/products/__init__.py` (empty)
- Create: `shopify/scripts/products/list.py`
- Create: `tests/shopify/scripts/test_products_list.py`

- [ ] **Step 1: Write failing unit test (mocked client)**

```python
from unittest.mock import patch
import sys
import json

from shopify.scripts.products import list as listcmd


def test_list_products_calls_graphql(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    fake = {"products": {"edges": [
        {"node": {"id": "gid://shopify/Product/1", "title": "Pearl", "status": "ACTIVE", "vendor": "Acme", "totalInventory": 12, "handle": "pearl"}},
    ], "pageInfo": {"hasNextPage": False, "endCursor": None}}}
    with patch("shopify.scripts.products.list.load_config") as cfg, \
         patch("shopify.scripts.products.list.ShopifyClient") as client:
        cfg.return_value.store.shopify_domain = "x.myshopify.com"
        cfg.return_value.domains = {"shopify": type("D", (), {"api_version": "2025-10", "enabled": True})()}
        client.return_value.graphql.return_value = fake
        with patch.object(sys, "argv", ["list.py", "--output", "json", "--limit", "10"]):
            assert listcmd.main() == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed[0]["title"] == "Pearl"
```

- [ ] **Step 2: Implement**

`shopify/scripts/products/list.py`:
```python
"""List products with filters."""
from __future__ import annotations

import argparse
import sys

from core.config import load_config
from shopify.utils.cli import add_common_flags, format_output
from shopify.utils.client import ShopifyClient

_QUERY = """
query Products($first: Int!, $query: String) {
  products(first: $first, query: $query) {
    edges {
      node {
        id
        title
        handle
        status
        vendor
        totalInventory
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Shopify products")
    add_common_flags(parser)
    parser.add_argument("--status", choices=("ACTIVE", "DRAFT", "ARCHIVED"))
    parser.add_argument("--vendor")
    parser.add_argument("--tag")
    parser.add_argument("--query", help="Raw Shopify product query string")
    args = parser.parse_args(argv)

    q_parts = []
    if args.status:
        q_parts.append(f"status:{args.status.lower()}")
    if args.vendor:
        q_parts.append(f"vendor:'{args.vendor}'")
    if args.tag:
        q_parts.append(f"tag:'{args.tag}'")
    if args.query:
        q_parts.append(args.query)
    query_string = " ".join(q_parts) or None

    cfg = load_config(args.config)
    client = ShopifyClient(config=cfg)
    try:
        data = client.graphql(_QUERY, {"first": args.limit, "query": query_string})
    finally:
        client.close()

    rows = [e["node"] for e in data["products"]["edges"]]
    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Run tests + commit**

```bash
mkdir -p shopify/scripts/products tests/shopify/scripts
touch shopify/scripts/products/__init__.py tests/shopify/scripts/__init__.py
uv run pytest tests/shopify/scripts/test_products_list.py -v
git add shopify/scripts/products/ tests/shopify/scripts/test_products_list.py
git commit -m "feat(shopify): products/list.py"
```

---

## Task 2: `shopify/scripts/products/get.py`

GraphQL query reads `product(handle: $handle)` OR `product(id: $id)` plus `variants(first: 100) { ... metafields(first: 50) { edges { node { namespace key value } } } }` and `translations(locale: $locale) { key value }`.

- [ ] **Step 1: Test (mocked):** verify a JSON response is parsed and printed; verify it accepts both `--id` and `--handle` and errors when both are missing.

- [ ] **Step 2: Implement.** Argparse flags: `--id`, `--handle`, `--locale`, plus common flags. Output: full product as JSON by default; table format collapses to id/title/status/variant count.

- [ ] **Step 3: Commit**

```bash
git add shopify/scripts/products/get.py tests/shopify/scripts/test_products_get.py
git commit -m "feat(shopify): products/get.py deep read"
```

GraphQL operation:
```graphql
query Product($id: ID, $handle: String, $locale: String) {
  product(id: $id, handle: $handle) {
    id title handle status vendor productType tags
    variants(first: 100) {
      edges { node {
        id sku price inventoryQuantity
        metafields(first: 50) { edges { node { namespace key value type } } }
      } }
    }
    metafields(first: 50) { edges { node { namespace key value type } } }
    translations(locale: $locale) { key value locale }
  }
}
```

---

## Task 3: `shopify/scripts/products/update.py`

GraphQL: `productUpdate(input: ProductInput!)` mutation.

- [ ] **Step 1: Test:** mocked — verify mutation input shape; `--dry-run` does not call `graphql`.

- [ ] **Step 2: Implement.** Flags: `--id` (required), `--title`, `--description`, `--status`, `--tags` (comma list), `--vendor`. Build `ProductInput` from non-None values. Honor `--dry-run` (print the would-be input and exit 0).

- [ ] **Step 3: Commit**

```graphql
mutation ProductUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id title status }
    userErrors { field message }
  }
}
```

---

## Task 4: `shopify/scripts/products/bulk_prices.py`

The most complex catalog script — uses `productVariantsBulkUpdate` in chunks of 250 variants, writes a state file for resumability.

> **Note on Bulk Operations API:** Spec § 6.5 lists `ShopifyClient.bulk_mutation()` (Shopify Bulk Operations file-upload mutations) as part of the client surface. This script intentionally does NOT use it — chunked `productVariantsBulkUpdate` is the correct shape for variant pricing updates. `bulk_mutation()` is deferred until a future script genuinely needs JSONL-style bulk writes; when that happens, implement it on `ShopifyClient` as a separate sub-task in that plan (test cases mirror `bulk_query` from Plan 3 Task 2 Step 0).

- [ ] **Step 1: Test:** mocked — verify
  - CSV with 3 rows produces one mutation call.
  - State file is written under `.state/shopify/bulk_prices_<timestamp>.json` with completed SKUs.
  - `--resume <state-file>` reads state and skips completed SKUs.
  - `--dry-run` prints the input batch and writes no state.

- [ ] **Step 2: Implement.** CSV columns: `variant_id` OR `sku`,`price`,`compare_at_price` (optional). Resolve `sku` → `variant_id` via a `productVariants(query: "sku:<sku>")` lookup; cache resolutions in the state file.

CSV-to-mutation chunking:
```graphql
mutation Bulk($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    productVariants { id price compareAtPrice }
    userErrors { field message }
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add shopify/scripts/products/bulk_prices.py tests/shopify/scripts/test_products_bulk_prices.py
git commit -m "feat(shopify): products/bulk_prices.py with state-based resumability"
```

---

## Task 5: `skills/shopify-products/SKILL.md`

Follows the template from `skills/shopify-auth/SKILL.md`. Triggers: "list products", "find product by SKU", "update product description", "bulk price update", "change product status to active". Documents the four canonical commands above with copy-paste examples.

- [ ] **Step 1: Write SKILL.md**
- [ ] **Step 2: Commit**

```bash
git add skills/shopify-products/SKILL.md
git commit -m "feat(skills): shopify-products"
```

---

## Task 6: `shopify/scripts/collection/list.py`

- [ ] **Step 1: Test (mocked):** verify both smart and custom collections appear; pagination works.

- [ ] **Step 2: Implement.** Flags: `--type` (smart/custom/all, default all), plus common flags.

```graphql
query Collections($first: Int!, $query: String) {
  collections(first: $first, query: $query) {
    edges { node { id title handle productsCount sortOrder updatedAt } }
    pageInfo { hasNextPage endCursor }
  }
}
```

- [ ] **Step 3: Commit**

---

## Task 7: `shopify/scripts/collection/create.py`

Two mutations depending on type: `collectionCreate(input: CollectionInput!)` (custom) and same with `ruleSet` for smart.

- [ ] **Step 1: Test:** mocked — verify smart collection produces ruleSet in input.
- [ ] **Step 2: Implement.** Flags: `--title` (required), `--handle`, `--description`, `--rules` (JSON path for smart collection rules), `--sort-order`.
- [ ] **Step 3: Commit**

---

## Task 8: `shopify/scripts/collection/update.py`

- [ ] **Step 1: Test:** mocked — verify only provided fields are sent.
- [ ] **Step 2: Implement.** Same flags as create, plus `--id` required. Uses `collectionUpdate`.
- [ ] **Step 3: Commit**

---

## Task 9: `shopify/scripts/collection/add_products.py`

Uses `collectionAddProducts(id: ID!, productIds: [ID!]!)` in chunks of 250.

- [ ] **Step 1: Test:** mocked — CSV/stdin list of product IDs/handles is chunked; handle→ID resolution via lookup; dry-run prints batch sizes.
- [ ] **Step 2: Implement.** Flags: `--collection-id`, `--from-csv <path>` OR `--handles <comma list>`, plus common flags.
- [ ] **Step 3: Commit**

---

## Task 10: `skills/shopify-collections/SKILL.md`

Triggers: "create collection", "list collections", "add products to collection", "update collection rules". Reference `collections/*` scripts.

- [ ] Write + commit.

---

## Task 11: `shopify/scripts/metafields/list.py`

GraphQL: `metafields(first: $first, namespace: $ns, ownerType: $owner)` for a resource ID via the resource's `metafields` connection (since global metafields lookup requires per-owner queries).

- [ ] **Step 1: Test:** mocked — verify owner-type routing (PRODUCT, VARIANT, COLLECTION, CUSTOMER, ORDER, SHOP).
- [ ] **Step 2: Implement.** Flags: `--owner-type`, `--owner-id`, `--namespace` (optional), `--key` (optional).
- [ ] **Step 3: Commit**

---

## Task 12: `shopify/scripts/metafields/set.py`

Uses `metafieldsSet(metafields: [MetafieldsSetInput!]!)` (up to 25 per call).

- [ ] **Step 1: Test:** mocked — single set via flags, batch from stdin JSON.
- [ ] **Step 2: Implement.** Flags: `--owner-id`, `--namespace`, `--key`, `--value`, `--type` for single; `--batch -` to read JSON array from stdin.
- [ ] **Step 3: Commit**

```graphql
mutation MetafieldsSet($input: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $input) {
    metafields { id namespace key value type }
    userErrors { field message }
  }
}
```

---

## Task 13: `shopify/scripts/metaobjects/list.py`

`metaobjects(type: $type, first: $first)`.

- [ ] **Step 1: Test:** mocked.
- [ ] **Step 2: Implement.** Flags: `--type` (required), plus common.
- [ ] **Step 3: Commit**

---

## Task 14: `shopify/scripts/metaobjects/upsert.py`

Uses `metaobjectUpsert(handle: MetaobjectHandleInput!, metaobject: MetaobjectUpsertInput!)`.

- [ ] **Step 1: Test:** mocked — input shape includes `handle.type`, `handle.handle`, and `fields[]`.
- [ ] **Step 2: Implement.** Flags: `--type`, `--handle`, `--fields` (JSON object or path).
- [ ] **Step 3: Commit**

---

## Task 15: `shopify/scripts/metaobjects/delete.py`

Uses `metaobjectDelete(id: ID!)`.

- [ ] **Step 1: Test:** mocked.
- [ ] **Step 2: Implement.** Flag: `--id`.
- [ ] **Step 3: Commit**

---

## Task 16: `skills/shopify-metafields/SKILL.md`

Single skill covers both metafields and metaobjects per spec § 6.6. Triggers: "set product metafield", "list metafields", "create metaobject entry". Reference both `metafields/*` and `metaobjects/*` scripts.

- [ ] Write + commit.

---

## Task 17: `shopify/scripts/translations/list.py`

Uses each resource's `translations(locale:)` connection or `translatableResources(resourceType:)` for sweep.

- [ ] **Step 1: Test:** mocked.
- [ ] **Step 2: Implement.** Flags: `--resource-id` OR `--resource-type` (sweep), `--locale` (required).
- [ ] **Step 3: Commit**

---

## Task 18: `shopify/scripts/translations/register.py`

Uses `translationsRegister(resourceId: ID!, translations: [TranslationInput!]!)` (one resource per call; iterate over input).

- [ ] **Step 1: Test:** mocked — verify CSV input `resource_id,locale,key,value,translatable_content_digest` is grouped by resource_id and translated in batches.
- [ ] **Step 2: Implement.** Flag: `--from-csv` (required), `--dry-run`. CSV columns above. `translatable_content_digest` is required by the API — script fails loudly if a row is missing it.
- [ ] **Step 3: Commit**

```graphql
mutation Register($id: ID!, $translations: [TranslationInput!]!) {
  translationsRegister(resourceId: $id, translations: $translations) {
    translations { key locale value }
    userErrors { field message }
  }
}
```

---

## Task 19: `skills/shopify-translations/SKILL.md`

Triggers: "register translations from CSV", "list translations for product", "translate a metafield". Document the CSV format including the `translatable_content_digest` requirement.

- [ ] Write + commit.

---

## Task 20: Smoke + final sweep

- [ ] Run full test suite: `uv run pytest -v` — all unit tests must pass.
- [ ] Ruff: `uv run ruff check . && uv run ruff format --check .` — clean.
- [ ] If a dev shop is available, run each `list*.py` script with `--limit 1` and verify each returns a non-empty result.
- [ ] Update `CHANGELOG.md` with the catalog additions under `0.2.0`.
- [ ] Tag: `git tag -a v0.2.0-alpha -m "Shopify catalog"`.

---

## Definition of Done

- [ ] All 15 scripts under `shopify/scripts/{products,collections,metafields,metaobjects,translations}/` implemented and tested.
- [ ] 4 skills (`shopify-products`, `shopify-collections`, `shopify-metafields`, `shopify-translations`) written.
- [ ] CI green.
- [ ] CHANGELOG bumped.
