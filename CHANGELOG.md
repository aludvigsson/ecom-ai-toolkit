# Changelog

All notable changes documented here. Format follows [keep-a-changelog](https://keepachangelog.com/en/1.1.0/).

## [0.4.1] — 2026-05-28

### Added
- `HttpClient` gains `.put()`, `.patch()`, `.delete()` methods to mirror `.get/.post/.head` (Plan-4 S-3). Avoids re-invention in Plan 5 webhook scripts that target third-party platforms.
- `hydrogen/validate_url.py` gains `--no-follow-redirects` flag for strict mode (Plan-4 I-2).

### Fixed
- `hydrogen/validate_url.py` no longer retries on 5xx (Plan-4 I-1). Validators check current state; retries hide problems.
- `hydrogen/build_variant_url.py` strips trailing slashes from `store.primary_domain` and percent-encodes the product handle so non-ASCII handles produce RFC 3986-compliant URLs (Plan-4 S-1).
- `theme/update_asset.py` prints a stderr notice when both `--dry-run` and `--yes` are passed (Plan-4 S-2). `--dry-run` still wins; just no longer silent.

## [0.4.0] — 2026-05-28

### Added
- **Theme domain (Online Store 2.0):** `shopify/scripts/theme/{list,get_asset,update_asset}.py` — list themes by role, read theme file content (text body), write file with diff preview gated behind `--dry-run` + `--yes`. Skill: `shopify-theme`.
- **Hydrogen domain:** `shopify/scripts/hydrogen/{build_variant_url,validate_url}.py` — pure-Python URL composition + HEAD-check validation. No Shopify Admin API required. Skill: `shopify-hydrogen`.
- **`shopify/utils/diff.py`** — unified diff helper using stdlib difflib. Used by `theme/update_asset.py` and available to future scripts.
- **`core.http.HttpClient.head()`** — wraps the existing `.request()` retry path with the HEAD method, used by `hydrogen/validate_url.py`.

### Boundaries
- `theme/*` scripts are Online Store 2.0 only. Hydrogen storefront edits live in your separate Hydrogen repo and are NOT in scope for the toolkit.
- `hydrogen/*` helpers are URL-builders/validators only. They do not edit Hydrogen source code.

## [0.3.2] — 2026-05-28

### Added
- `shopify/scripts/setup.py` — interactive first-run setup for `store-config.yaml` + `.env.local`. Supports two auth modes: custom-app token paste (non-expiring) and Shopify CLI browser OAuth (expires in ~24h, suited for interactive use; token extracted from CLI config).

## [0.3.1] — 2026-05-28

### Fixed
- `discounts/update.py` now requires `--applies-to` when `--value` changes so partial `customerGets` updates don't fail Shopify's input validation (Plan-3 deferred concern I-3).
- `bulk_query` does one final un-timed poll after `max_wait` expires before raising, and retries the JSONL download up to 3 times on transient network errors (Plan-3 deferred concerns I-1, I-2).
- `discounts/create.py` argparse-errors at parse time for invalid flag combinations (`--value` on free-shipping, `--usage-limit`/`--applies-once-per-customer` on automatic, percentage `--value > 100`) instead of silently dropping or failing later (Plan-3 deferred concern I-4, suggestion S-1).
- `inventory/set.py` `--location-name` match is now case-insensitive (Plan-3 deferred concern I-5).

### Changed
- `--verbose` (shared flag) now actually raises the `ecom.*` logger to DEBUG via the new `configure_logging_from_args(args)` helper called by every script (Plan-2 deferred concern I-1).
- `--market` (shared flag) removed from `add_common_flags`. No script read it; future scripts that need market scoping should add `--market` per-script (Plan-2 deferred concern I-1).
- `core.state.save_state` writes a `schema_version` field (default 1). New `load_state_v(*, expected_version)` raises `StateSchemaError` on mismatch so resume loaders fail loudly on stale-shape files. `bulk_prices.py` migrated (Plan-2 deferred concern I-2).

### Note
- `SkuNotFoundError`'s base class changed in 0.3.0 from `RuntimeError` to `LookupError` per stdlib "not found" convention. User code catching `RuntimeError` should switch to `LookupError` or the specific class.

## [0.3.0] — 2026-05-28

### Added
- **Bulk Operations API:** `ShopifyClient.bulk_query()` runs `bulkOperationRunQuery`, polls `currentBulkOperation` until complete, then yields parsed JSONL rows. `ShopifyBulkOperationError` raised on FAILED/CANCELED/timeout.
- **Orders domain:** `shopify/scripts/orders/{list,report}.py` — date/status/customer-filtered queries plus markdown GMV/refunds/top-SKUs summaries via `bulk_query` for unbounded ranges. Skill: `shopify-orders`.
- **Customers domain:** `shopify/scripts/customers/list.py` — email/tag/state/min-orders filtered reads with `numberOfOrders` post-filter. Skill: `shopify-customers` (read-only in v0.3).
- **Inventory domain:** `shopify/scripts/inventory/{levels,set}.py` — per-SKU inventory across locations and on-hand quantity adjustment via `inventorySetOnHandQuantities`. Two-step resolution (SKU→inventoryItem, name→locationId). Skill: `shopify-inventory`.
- **Discounts domain:** `shopify/scripts/discounts/{list,create,update,delete}.py` — covers both code and automatic discount catalogs across four kinds (percentage, fixed, bxgy, free-shipping). `update.py` and `delete.py` auto-detect the kind via the dual `codeDiscountNode`/`automaticDiscountNode` lookup. Skill: `shopify-discounts`.

### Changed
- `AmbiguousSkuError` and `SkuNotFoundError` promoted from `products/bulk_prices.py` to `shopify.utils.client` so other domains (inventory, discounts) can reuse them. `SkuNotFoundError` now subclasses `LookupError` per stdlib "not found" convention; `AmbiguousSkuError` remains on `RuntimeError`.

### Conventions
- All read scripts honor `--limit` (default 50); some support `--from`/`--to` ISO date ranges; all support `--output {table,json,markdown}` via the shared `format_output` helper.
- All mutation scripts honor `--dry-run` (skips graphql, prints would-be input) and surface mutation-level userErrors via the free function `shopify.utils.client.check_user_errors(data, mutation=...)`.
- Destructive mutations (`metaobjects/delete.py`, `discounts/delete.py`) require an explicit `--yes` flag; `--dry-run` does not require it.
- Detect-then-dispatch pattern: `discounts/{update,delete}.py` query both `codeDiscountNode` and `automaticDiscountNode` to determine the discount kind before dispatching to the matching mutation.

## [0.2.0] — 2026-05-28

### Added
- **Shared catalog helpers:** `shopify/utils/cli.py` (add_common_flags + format_output for table/json/markdown), `shopify/utils/csv_io.py` (read_csv_dicts), `shopify/utils/search.py` (escape_search_value for Shopify search-syntax injection safety).
- **Products domain:** `shopify/scripts/products/{list,get,update,bulk_prices}.py` — read with filters, deep read by id/handle/locale, partial updates with --dry-run, CSV-driven bulk price update with resumable state and SKU disambiguation. Skill: `shopify-products`.
- **Collections domain:** `shopify/scripts/collection/{list,create,update,add_products}.py` — smart + custom collections via --rules, partial updates, chunked 250-per-call bulk add by id or handle. Skill: `shopify-collections`.
- **Metafields + metaobjects:** `shopify/scripts/metafields/{list,set}.py` (owner-typed reads, 25-per-call batched upsert) and `shopify/scripts/metaobjects/{list,upsert,delete}.py` ((type,handle)-keyed upsert, --yes-gated delete). Skill: `shopify-metafields`.
- **Translations:** `shopify/scripts/translations/{list,register}.py` — single-resource read or sweep by type, CSV-driven `translationsRegister` with translatableContentDigest validation. Skill: `shopify-translations`.

### Changed
- `ShopifyUserError` summary formatting branches explicitly on empty/multi `field` (was using `.strip(": ")` hack).
- `ShopifyGraphQLError.data` widened to `dict[str, Any] | None` with explicit docstring about None-ness.
- `check_user_errors` available as a free function (`from shopify.utils.client import check_user_errors`); the `ShopifyClient.check_user_errors` staticmethod is now a back-compat shim. Mutation scripts import the free function directly instead of the v0.1.1 alias dance.

### Fixed
- `shopify/utils/search.escape_search_value()` prevents Shopify search-syntax injection / parsing breakage when user-text contains `'` or `\`. Used by `products/list.py` (`--vendor`, `--tag`) and `products/bulk_prices.py` (SKU lookup).
- `products/bulk_prices.py` SKU lookup now queries `first: 2` and raises `AmbiguousSkuError` instead of silently picking the first match. Missing SKUs raise `SkuNotFoundError` for clarity.
- `products/update.py` `--description` renamed to `--description-html` to signal that the value is sent verbatim to `descriptionHtml` and is NOT auto-escaped.
- `products/bulk_prices.py` `_save_state_to_path` writes atomically (tmp + `os.replace`) — previously a SIGKILL mid-write would corrupt the resume file.
- Dropped duplicate `_LOOKUP_BY_ID_QUERY` constant in `products/bulk_prices.py`.

## [0.1.1] — 2026-05-28

### Fixed
- `core.secrets._env_loaded` flag no longer causes test flakes — added autouse fixture that resets the flag between tests (Plan-1 deferred-concerns #1).
- `core.http._RedactingFilter` substrings narrowed so legitimate log lines mentioning pagination "cursor tokens" are not false-positive-redacted (Plan-1 deferred-concerns #2).

### Added
- `shopify.utils.client.ShopifyClient` now implements the context-manager protocol (`with ShopifyClient(cfg) as c:`); `whoami.py` updated to use it (Plan-1 deferred-concerns #4).
- `ShopifyGraphQLError` now carries the partial `.data` when Shopify returns both `data` and `errors` in the same response (Plan-1 deferred-concerns #15).
- `ShopifyUserError` + `ShopifyClient.check_user_errors(payload, mutation=...)` helper for surfacing mutation-level userErrors consistently (Plan-1 deferred-concerns #16).

## [0.1.0] — 2026-05-28

### Added
- Foundations: `core/` (config, secrets, state, http, logging) and packaging.
- Shopify domain skeleton: `ShopifyClient`, `whoami.py` smoke test, `shopify-auth` skill.
- Claude Code plugin manifest declaring `Shopify/Shopify-AI-Toolkit` as dependency.
- CI: lint + core unit tests on push.
