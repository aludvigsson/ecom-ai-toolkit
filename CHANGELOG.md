# Changelog

All notable changes documented here. Format follows [keep-a-changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] — 2026-05-28

### Added
- **Shared catalog helpers:** `shopify/utils/cli.py` (add_common_flags + format_output for table/json/markdown), `shopify/utils/csv_io.py` (read_csv_dicts), `shopify/utils/search.py` (escape_search_value for Shopify search-syntax injection safety).
- **Products domain:** `shopify/scripts/products/{list,get,update,bulk_prices}.py` — read with filters, deep read by id/handle/locale, partial updates with --dry-run, CSV-driven bulk price update with resumable state and SKU disambiguation. Skill: `shopify-products`.
- **Collections domain:** `shopify/scripts/collections/{list,create,update,add_products}.py` — smart + custom collections via --rules, partial updates, chunked 250-per-call bulk add by id or handle. Skill: `shopify-collections`.
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
