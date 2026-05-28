# Changelog

All notable changes documented here. Format follows [keep-a-changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.1] — 2026-05-28

### Fixed
- `core.secrets._env_loaded` flag no longer causes test flakes — added autouse fixture that resets the flag between tests (Plan-1 deferred-concerns #1).
- `core.http._RedactingFilter` substrings narrowed so legitimate log lines mentioning pagination "cursor tokens" are not false-positive-redacted (Plan-1 deferred-concerns #2).

### Added
- `shopify.utils.client.ShopifyClient` now implements the context-manager protocol (`with ShopifyClient(cfg) as c:`); `whoami.py` updated to use it (Plan-1 deferred-concerns #4).
- `ShopifyGraphQLError` now carries the partial `.data` when Shopify returns both `data` and `errors` in the same response (Plan-1 deferred-concerns #15).
- `ShopifyUserError` + `ShopifyClient.check_user_errors(payload, mutation=...)` helper for surfacing mutation-level userErrors consistently (Plan-1 deferred-concerns #16).

## [0.1.0] — unreleased

### Added
- Foundations: `core/` (config, secrets, state, http, logging) and packaging.
- Shopify domain skeleton: `ShopifyClient`, `whoami.py` smoke test, `shopify-auth` skill.
- Claude Code plugin manifest declaring `Shopify/Shopify-AI-Toolkit` as dependency.
- CI: lint + core unit tests on push.
