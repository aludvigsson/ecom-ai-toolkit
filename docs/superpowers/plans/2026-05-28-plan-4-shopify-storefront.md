# Plan 4: Shopify Storefront Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship storefront helpers: Online Store 2.0 theme asset CRUD and Hydrogen-aware URL builders/validators.

**Architecture:** OS 2.0 theme work uses Admin GraphQL `theme(id:)` and `themeFilesUpsert` / `themeFilesDelete`. Hydrogen helpers are pure-Python URL operations against a configured Hydrogen storefront URL (no Shopify API needed for those; they're `httpx` HEAD requests + string assembly).

**Tech Stack:** Same as Plan 1.

**Spec reference:** §§ 6.1 (`theme/`, `hydrogen/`), 6.4 (Hydrogen boundaries: helpers only, no source edits), 6.2.

**Depends on:** Plan 1.

---

## File Structure

| Path | Responsibility |
|---|---|
| `shopify/scripts/theme/list.py` | List themes |
| `shopify/scripts/theme/get_asset.py` | Read a single theme asset |
| `shopify/scripts/theme/update_asset.py` | Write a theme asset with `--dry-run` + diff |
| `shopify/scripts/hydrogen/build_variant_url.py` | Build locale-aware variant URLs from product handle + variant SKU/id |
| `shopify/scripts/hydrogen/validate_url.py` | HEAD-check Hydrogen URLs |
| `shopify/utils/diff.py` | Unified diff helper used by `update_asset.py` |
| `skills/shopify-theme/SKILL.md` | Wraps `theme/*` |
| `skills/shopify-hydrogen/SKILL.md` | Wraps `hydrogen/*` |
| `tests/shopify/scripts/test_theme_*.py`, `test_hydrogen_*.py` | One test module per script |
| `tests/shopify/utils/test_diff.py` | Unit test for diff helper |

---

## Task 1: `shopify/utils/diff.py`

Tiny helper that wraps `difflib.unified_diff` and returns a string. Used by theme update.

- [ ] **Step 1: Test:** verify `make_diff(old, new, path)` returns a diff with `---` and `+++` header lines and `-old`, `+new` body lines.
- [ ] **Step 2: Implement** (~10 lines).
- [ ] **Step 3: Commit**

```python
"""Unified diff helper."""
from __future__ import annotations

import difflib


def make_diff(old: str, new: str, path: str = "asset") -> str:
    return "\n".join(
        difflib.unified_diff(
            old.splitlines(),
            new.splitlines(),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="",
        )
    )
```

---

## Task 2: `shopify/scripts/theme/list.py`

```graphql
query Themes($first: Int!) {
  themes(first: $first) {
    edges { node { id name role processingFailed previewable updatedAt } }
  }
}
```

- [ ] **Step 1: Test (mocked):** verify roles (`MAIN`, `UNPUBLISHED`, `DEMO`, `DEVELOPMENT`) appear in output.
- [ ] **Step 2: Implement.** Flags: `--role` (optional filter), plus common.
- [ ] **Step 3: Commit**

---

## Task 3: `shopify/scripts/theme/get_asset.py`

Read via `theme(id:){ files(filenames: [...]) { ... } }`:
```graphql
query Asset($themeId: ID!, $filenames: [String!]!) {
  theme(id: $themeId) {
    files(filenames: $filenames, first: 1) {
      edges { node { filename body { ... on OnlineStoreThemeFileBodyText { content } } size contentType } }
    }
  }
}
```

- [ ] **Step 1: Test (mocked):** verify single file returned, body content printed.
- [ ] **Step 2: Implement.** Flags: `--theme-id`, `--filename` (e.g. `templates/product.json`, `sections/header.liquid`), `--output` (text or json).
- [ ] **Step 3: Commit**

---

## Task 4: `shopify/scripts/theme/update_asset.py`

Uses `themeFilesUpsert(themeId: ID!, files: [OnlineStoreThemeFilesUpsertFileInput!]!)`.

- [ ] **Step 1: Test (mocked):**
  - Without `--yes`: prints diff to stderr, does not call upsert mutation, exits non-zero.
  - With `--yes`: calls mutation.
  - `--dry-run` always behaves like the without-`--yes` case regardless of confirmation.
- [ ] **Step 2: Implement.** Flags: `--theme-id`, `--filename`, `--from-file <local path>`, `--yes`, `--dry-run`. Fetches current asset, diffs, applies upsert if confirmed.
- [ ] **Step 3: Commit**

```graphql
mutation Upsert($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
  themeFilesUpsert(themeId: $themeId, files: $files) {
    upsertedThemeFiles { filename }
    userErrors { field message code }
  }
}
```

---

## Task 5: `skills/shopify-theme/SKILL.md`

Triggers: "list themes", "read template product.json", "update sections/header.liquid", "deploy theme change". Hard rule documented in skill: `update_asset.py` is for Online Store 2.0 only — for Hydrogen storefronts, the skill must redirect the user to their Hydrogen repo.

- [ ] Write + commit.

---

## Task 6: `shopify/scripts/hydrogen/build_variant_url.py`

Pure-Python (no Shopify API needed). Reads `store-config.yaml`:
- `store.primary_domain`
- `store.storefront_type` (must be `hydrogen`)
- `markets[*].url_prefix`

Variant-URL pattern for Hydrogen storefronts is typically `https://<domain>/<market_prefix>/products/<handle>?variant=<numeric-id>`, or some stores embed the variant slug directly in the path. The script's job is to produce the canonical URL form for THIS store as configured.

- [ ] **Step 1: Test:** verify a URL is produced for a sample handle + market.
- [ ] **Step 2: Implement.** Flags: `--handle` (required), `--variant-id` OR `--variant-sku`, `--market` (required). Falls back to `store.default_locale` market if `--market` is omitted. Errors clearly if `storefront_type != "hydrogen"`.
- [ ] **Step 3: Commit**

---

## Task 7: `shopify/scripts/hydrogen/validate_url.py`

HEAD-request validation. Uses `core.http.HttpClient` (no auth needed).

- [ ] **Step 1: Test (httpx_mock):** verify 200 prints OK; 404 prints NOT FOUND; 3xx follows redirects up to a limit and reports the final URL.
- [ ] **Step 2: Implement.** Flags: `--url` (repeatable) OR `--from-csv <path>` with `url` column. Exits non-zero if any URL returns >= 400.
- [ ] **Step 3: Commit**

---

## Task 8: `skills/shopify-hydrogen/SKILL.md`

Triggers: "build variant URL for SKU X in DE market", "validate these Hydrogen URLs", "URLs broken on storefront". Document the spec § 6.4 boundary: this skill helps with URLs only — Hydrogen source edits belong in the Hydrogen storefront repo, not here.

- [ ] Write + commit.

---

## Task 9: Smoke + final sweep

- [ ] Run full test suite, ruff clean.
- [ ] If a dev shop with a theme is available, run `theme/list.py` and `theme/get_asset.py --filename templates/index.json`.
- [ ] CHANGELOG: add storefront items under `0.4.0`.
- [ ] Tag: `git tag -a v0.4.0-alpha -m "Shopify storefront"`.

---

## Definition of Done

- [ ] 5 scripts under `shopify/scripts/{theme,hydrogen}/` implemented and tested.
- [ ] 2 skills (`shopify-theme`, `shopify-hydrogen`) written.
- [ ] `shopify/utils/diff.py` covered by unit test.
- [ ] CI green.
- [ ] CHANGELOG bumped.
