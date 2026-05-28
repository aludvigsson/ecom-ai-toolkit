# Plan 4 — Deferred concerns (v0.4.0-alpha → v0.4.1 / Plan 5 prerequisites)

Findings from the final Plan 4 whole-plan code review. None blocked v0.4.0-alpha; addressing these before Plan 5 (webhooks) keeps the HTTP and validation patterns clean.

## Important (land before Plan 5 starts)

### I-1. `validate_url.py` HEAD requests retry on 5xx — wrong for "is this URL alive" checks
**Where:** `shopify/scripts/hydrogen/validate_url.py` uses `HttpClient.head()` which inherits `_RETRY_STATUSES = {429, 500, 502, 503, 504}` plus 4 retries.

**Why:** A genuinely broken Hydrogen URL returning 503 will trigger ~30s of retries per URL before reporting failure. For a validation tool checking N URLs in a CSV, this is painful and the result is misleading (looks like a transient issue when it's persistent).

**Fix options:**
- (a) Pass `max_retries=0` when constructing the client in `validate_url.py`.
- (b) Add a `retries=` kwarg to `HttpClient.head()` (and probably `.get/.post/.put/.delete` for symmetry).
- (c) Add a `--retries N` CLI flag to `validate_url.py`.

Prefer (a) for the immediate fix; (b) for the long-term API hygiene.

### I-2. `validate_url.py` needs a `--no-follow-redirects` flag
**Where:** `shopify/scripts/hydrogen/validate_url.py`.

**Why:** A parked-domain or expired-SSL 301 → 200 currently reports `ok: True` with the unexpected `final_url`. Worth letting the user opt into strict mode where redirects are reported as the URL's status, not the final hop's.

**Fix:** Add `--no-follow-redirects` to argparse, pass `follow_redirects=not args.no_follow_redirects` into the HEAD call. Default keeps current behavior.

## Suggestions

### S-1. `build_variant_url.py` doesn't normalize trailing slash on `primary_domain`
**Where:** `shopify/scripts/hydrogen/build_variant_url.py` URL composition.

**Why:** If `store.primary_domain` is `"example.com/"` (user typo in YAML), output becomes `https://example.com//se/products/...`.

**Fix:** `domain = cfg.store.primary_domain.rstrip("/")` in the URL builder. Also worth `urllib.parse.quote(handle, safe="")` to guard handles with non-ASCII chars.

### S-2. `update_asset.py` precedence note for `--dry-run` + `--yes`
**Where:** `shopify/scripts/theme/update_asset.py`.

**Why:** Current behavior: `--dry-run` returns 0 before checking `--yes`. Correct precedence, but silent when both are passed.

**Fix:** Add one stderr line: `"--dry-run takes precedence over --yes"`.

### S-3. `HttpClient` method symmetry
**Where:** `core/http.py`.

**Why:** Added `.head()` only in Plan 4. Plan 5 (webhooks) will likely need `.put()` or `.delete()` for webhook subscription management on third-party platforms.

**Fix:** Add `.put()`, `.patch()`, `.delete()` methods that delegate to `.request()`. 4 lines each. Avoids Plan 5 backfilling.

### S-4. `theme/list.py` `--role` post-filter interaction with `--limit`
**Where:** `shopify/scripts/theme/list.py`.

**Why:** Fetches `--limit N` themes then filters by role in-memory. User may see fewer than N rows when filtering.

**Fix:** Comment in the script + pitfall in the `shopify-theme` skill.

## Carried over from Plan 3 (still open)
- Plan 3 I-4 fix scope: `discounts/create.py` validations landed in v0.3.1 polish. Closed.
- All Plan 3 Important items addressed in v0.3.1.
- Plan 2 carryover I-4 (translations/register.py bare RuntimeError) still open — non-blocking.

## Triage
- I-1 + I-2 + S-3: bundle into v0.4.1 polish before Plan 5 starts. ~15 min of work.
- S-1, S-2, S-4: opportunistic during Plan 5.
- Plan 2 I-4 carryover: tackle when Plan 5 needs CSV-input validation patterns.
