# Plan 1 — Deferred concerns (v0.1.0-alpha → v0.1.0 final)

Findings from per-batch reviews and the final whole-plan review that were deferred during implementation. Address before v0.1.0 final or fold into Plans 2–5.

## Important (land before v0.1.0 final)

### 1. **[RESOLVED in v0.1.1]** `core/secrets.py` — `_env_loaded` test-flake risk
**Where:** `core/secrets.py:13` (module-level `_env_loaded` flag).
**Why:** Flag conflates "we auto-tried" with "don't try again." Any future test that writes a `.env.local` to a `tmp_path` and relies on `get_secret()` auto-loading it will silently no-op if any prior test already triggered the auto-load.
**Fix options:**
- Add a `conftest.py` autouse fixture that resets `core.secrets._env_loaded = False` between tests, OR
- Change `_ensure_loaded` to recheck on cwd change, OR
- Have `load_env_local(explicit_path)` always parse the explicit path; only gate the lazy auto-load path.

### 2. **[RESOLVED in v0.1.1]** `core/http.py` — `_RedactingFilter` is defense-in-depth only
**Where:** `core/http.py:_RedactingFilter`.
**Why:** The current `_log_request` only logs `method`, `host+path`, `status`, `elapsed` — no headers, no body. The filter is effectively dormant on the paths we control. If a future domain author logs `_log.info("payload=%s", body)` containing a token *value*, nothing redacts it. The existing test asserts absence of "SECRET", not a positive redaction.
**Fix:** Either (a) document the filter as defense-in-depth only and tell domain authors "never log bodies" + add a positive redaction unit test, or (b) extend the filter to scan known secret values registered at startup. Prefer (a) + the positive test.
**Sub-finding:** narrow `_SENSITIVE_KEYS` from bare `"token"` to `"token="`/`"token:"` to avoid false-positive redaction on legitimate log lines like `"sync token cursor=..."` (Shopify pagination cursors mention "token").

## Suggestions (nice-to-have)

### 3. `core/config.py` — memoize `StoreConfig.market()`
**Where:** `core/config.py:StoreConfig.market`.
**Why:** O(n) linear scan; fine for 6 markets, but bulk scripts in Plans 2–3 will call this in tight loops.
**Fix:** Build `_market_index: dict[str, Market]` via `@functools.cached_property`, then `O(1)` lookup.

### 4. **[RESOLVED in v0.1.1]** `shopify/utils/client.py` — add context-manager protocol to `ShopifyClient`
**Where:** `shopify/utils/client.py:ShopifyClient`.
**Why:** `HttpClient` already implements `__enter__`/`__exit__`. Adding the same on `ShopifyClient` removes the `try/finally client.close()` boilerplate from every future script (`with ShopifyClient(cfg) as c:`). Standardizing now prevents Plans 2–5 from each re-inventing the try/finally.
**Fix:** 4 lines.

### 5. `core/state.py` — widen `load_state` return type
**Where:** `core/state.py:load_state`.
**Why:** Returns `dict | None` but the file contents can be any JSON value. First script that wants to persist a list (e.g. "last 100 webhook IDs") will fight the type hint.
**Fix:** Widen to `Any | None`, or document the JSON-object constraint in the docstring.

### 6. `core/__init__.py` — export `DomainConfig` (or remove `Market`/`Store`)
**Where:** `core/__init__.py:__all__`.
**Why:** Currently exports `Market` and `Store` but not `DomainConfig`. Inconsistent. Domain authors writing `if cfg.domains["klaviyo"].enabled:` will want the type.
**Fix:** Either export all three or only `StoreConfig`.

### 7. `README.md` — install step 4 is incomplete
**Where:** `README.md` install section, step 4.
**Why:** Says "Then ask: 'verify my Shopify connection'" without telling the user to install the plugin first. A new user will be confused about how Claude Code picks up the skill.
**Fix:** Drop step 4 OR add the `/plugin install` line first.

### 8. `pyproject.toml` — empty-list extras silently no-op
**Where:** `pyproject.toml:[project.optional-dependencies]`.
**Why:** `klaviyo = []`, `meta-ads = []`, etc. are reserved placeholders. `uv sync --extra klaviyo` today silently installs nothing.
**Fix:** Gate extras until each domain lands, or document the reservation in a comment.

### 9. `core/state.py` — concurrent-writer race on fixed tmp filename
**Where:** `core/state.py:save_state`.
**Why:** Two scripts writing the same `(domain, name)` race on a fixed `<name>.json.tmp` filename. The existing test's glob `*.tmp*` anticipated unique tmp names, but the impl uses a fixed one.
**Fix:** Use `tempfile.NamedTemporaryFile(dir=p.parent, delete=False)` for a unique tmp name. Becomes meaningful when bulk scripts arrive in Plans 2–3.

### 10. `core/state.py` — no `fsync` for true crash-safety
**Where:** `core/state.py:save_state`.
**Why:** `os.replace` is atomic vs process crashes but not vs power loss. For dev tooling this is fine.
**Fix:** Optional. Add `fsync` on the tmp file before replace + `fsync` on the parent directory after, OR document the limitation in the docstring.

### 11. `core/config.py` — extensibility for per-domain config
**Where:** `core/config.py:DomainConfig`.
**Why:** Today only `enabled` + `api_version`. Per the spec § 5.1, per-market platform IDs go in `markets[]` blocks, NOT in `domains[]` — so this is spec-aligned. But if any future domain wants global (non-per-market) config, `DomainConfig` will need `model_config = ConfigDict(extra="allow")` or per-domain subclasses.
**Fix:** Defer until the first domain genuinely needs it.

### 12. `pyproject.toml` — `pytest-httpx>=0.32` floor vs `httpx>=0.27`
**Where:** `pyproject.toml`.
**Why:** Some pytest-httpx 0.32 releases require httpx ≥ 0.28; the explicit floor here is 0.27. `uv.lock` resolves to compatible versions, so this is theoretical.
**Fix:** Bump `httpx>=0.28` once verified, or rely on the lockfile.

### 13. CHANGELOG em-dash
**Where:** `CHANGELOG.md`.
**Why:** Uses `## [0.1.0] — unreleased` (em-dash). keep-a-changelog's canonical form is `## [0.1.0] - YYYY-MM-DD` or `## [Unreleased]` as a separate heading.
**Fix:** Cosmetic.

### 14. ruff pin in pre-commit is ~12 months old
**Where:** `.pre-commit-config.yaml`.
**Why:** Ruff `v0.6.9` (Oct 2024); local install is `0.15.x`. Pinning is intentional/reproducible, just stale.
**Fix:** `uv run pre-commit autoupdate` periodically.

## Architectural notes (for Plans 2–5 awareness, not fixes)

### 15. **[RESOLVED in v0.1.1]** `ShopifyClient.graphql` raises on `errors` even when `data` is present (partial-success)
Shopify can return both `data` and `errors`. Current implementation discards `data` in that case. Worth deciding the policy before the first paginated read script in Plan 2:
- Option A: Attach `data` to the exception (`ShopifyGraphQLError(msg, data=body.get("data"))`).
- Option B: Only raise when `data` is missing; otherwise log a warning and return `data`.
Prefer A.

### 16. **[RESOLVED in v0.1.1]** `userErrors` (mutation-level) not handled
Distinct from top-level `errors`. Shopify mutations return `data.<mutation>.userErrors: [{field, message}]` on validation failure with HTTP 200 and no top-level `errors`. First Plan 2 mutation will hit this. Decide a helper shape now so each script doesn't re-invent.

### 17. `core/logging.py` is not thread-safe on first call
`root.handlers.clear()` + module-global `_configured` flag race under multi-threaded servers (FastAPI/uvicorn in Plan 5). Single-threaded CLI usage is fine. Add a `threading.Lock` before Plan 5 ships.

### 18. `core.logging` shadows stdlib `logging`
Inside `core/`, `import logging` works because module resolution is absolute. `python -m core.logging` would be confused. Low-impact, flag-and-monitor.

### 19. `ShopifyClient.__init__` validates `shopify_domain` only implicitly via the URL it constructs
A malicious/typoed `shopify_domain` containing slashes or hash fragments could exfiltrate the token to an unintended host. Practical risk is low (config is user-owned) but a one-line pydantic validator on `Store.shopify_domain` (regex `^[a-z0-9-]+\.myshopify\.com$`) would harden this. Belongs in `core/config.py`, not in the client.

---

## How to address

- Items 1, 2, 7 (Important): one polish PR before v0.1.0 final.
- Items 3, 4, 6, 11, 15, 16: address as part of Plan 2 since Plan 2's catalog scripts are the first to mimic / rely on these patterns.
- Items 8, 12, 13, 14, 18, 19: opportunistic cleanup, batch into a "v0.1.0 polish" PR.
- Items 5, 9, 10, 17: address when first triggering use case arrives (state-with-list, bulk concurrent writers, fsync needs, FastAPI receiver).
