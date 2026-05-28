# Plan 3 — Deferred concerns (v0.3.0-alpha → v0.3.0 final / Plan 4 prerequisites)

Findings from the final Plan 3 whole-plan code review. None blocked v0.3.0-alpha; addressing these before Plan 4 keeps the patterns clean as they propagate to theme/hydrogen scripts.

## Important (land before v0.3.0 final)

### I-3. `discounts/update.py` silently sends `customerGets` partial input that Shopify rejects
**Where:** `shopify/scripts/discounts/update.py:_build_partial_input` around `inp.setdefault("customerGets", {})["value"] = ...`.

**Why:** If a user passes only `--value 25` to change a Basic discount's percentage, the script sends `{customerGets: {value: {percentage: 0.25}}}` with no `items` selector. Shopify rejects this as a malformed partial update — the user sees a `ShopifyUserError` on what they thought was a simple value change.

**Fix options:**
- (a) When `--value` is provided without `--applies-to`, fetch the current `items` selector via an extra query and round-trip it back in the partial input.
- (b) Require `--applies-to` whenever `--value` is changed; argparse-error if missing.
- (c) Document the workaround in the skill's Common Pitfalls section (TEMPORARY mitigation for v0.3.0-alpha).

Prefer (a) for production polish. (c) is fine for alpha.

### I-1. `bulk_query` polling has a deadline edge case
**Where:** `shopify/utils/client.py:bulk_query`.

**Why:** If `max_wait` expires *between* a RUNNING poll and the next sleep wake-up, the loop raises "did not complete within Xs" even though the *next* poll would have returned COMPLETED. With default 300s / 2s polling this is unlikely to bite; with tight `max_wait` it can.

**Fix:** Do one un-timed final poll after the deadline before raising, OR check `last.status` and surface it in the error.

### I-2. `bulk_query` lacks retry on JSONL download failure
**Where:** `shopify/utils/client.py:bulk_query` — `httpx.stream(...)`.

**Why:** A single 5xx or connection reset surfaces as a raw `httpx` exception (not `ShopifyBulkOperationError`), with the bulk op already consumed server-side (no resume).

**Fix:** Wrap the stream call in `core.http.HttpClient`'s retry logic, OR add a one-retry-with-jitter wrapper, OR document the limitation explicitly in the docstring so callers know to wrap.

### I-4. `discounts/create.py` silently accepts ignored flags
**Where:** `shopify/scripts/discounts/create.py:main`.

**Why:** `--usage-limit` and `--applies-once-per-customer` are code-discount-only but the script silently drops them when building an automatic input. `--value` is silently accepted (and ignored) for `--kind free-shipping`. Users get no feedback that their flag did nothing.

**Fix:** After argparse, validate flag combinations and `parser.error()` with clear messages naming the rejected flag.

### I-5. `inventory/set.py` `--location-name` is case-sensitive
**Where:** `shopify/scripts/inventory/set.py:_resolve_location_by_name`.

**Why:** Typing `"stockholm warehouse"` to match `"Stockholm Warehouse"` returns no match. Surprising for an admin-tool flag.

**Fix:** Lowercase both sides before comparing; keep "exact match" semantics (no substring).

## Suggestions

### S-1. Percentage value bounds check
**Where:** `discounts/create.py` and `discounts/update.py` `_value_block`.

**Fix:** Reject `--value > 100` or `< 0` for percentage discounts at parse time instead of letting Shopify surface the error.

### S-2. BXGY simplification scope
**Where:** `discounts/create.py --kind bxgy`.

**Notes:** Current shape supports simple "buy X get Y free with all-items selectors". Tiered, partial-percent, and complex-selection BXGY all need extension. If we grow it, rename to `--kind bxgy-simple` in v0.4 to signal scope.

### S-3. `discounts/list.py --limit` is per-catalog when `--type all`
**Where:** `discounts/list.py`.

**Fix:** Document or split — `--limit 50 --type all` currently returns up to 100 rows. Either halve the per-catalog limit or document.

### S-5. Decimal precision in `_format_money`
**Where:** `shopify/scripts/orders/report.py:_format_money`.

**Fix:** Currently `f"{Decimal(...):,.2f}"` converts back through float. For GMV beyond float precision, use `Decimal.quantize(Decimal("0.01"))` + string formatting. Tiny risk.

### S-7. Test coverage: userErrors on every new mutation script
**Where:** test suites for `discounts/update.py`, `discounts/delete.py`, `inventory/set.py`.

**Fix:** Add a parametrised "userError raises ShopifyUserError" test for each. Currently only the happy path is asserted for some.

### S-9. CHANGELOG: SkuNotFoundError base class change
**Where:** `CHANGELOG.md` 0.3.0 section.

**Fix:** Add a "Changed (potentially breaking)" line for the SkuNotFoundError RuntimeError → LookupError base widening, in case any user code catches `RuntimeError`.

## Carried-over from Plan 2 (still open)

- **Plan 2 I1** `--market` and `--verbose` dead flags. Plan 3 scripts did NOT cargo-cult new instances — just inherit the gap from `add_common_flags`. Still worth wiring before Plan 4.
- **Plan 2 I2** state-file `schema_version`. No new state files in Plan 3; bulk_prices.py still without.
- **Plan 2 I4** `translations/register.py` still uses bare RuntimeError for CSV validation.

## Triage

- I-3 (Important, blocking-ish for production): fix in v0.3.1 polish PR before Plan 4 starts, OR document as Common Pitfall in the discounts skill if Plan 4 takes priority.
- I-1, I-2, I-4, I-5: v0.3.1 polish bundle.
- S-1, S-3, S-5, S-7: opportunistic during Plan 4.
- Plan 2 carryovers (I1, I2, I4): if Plan 4 will write to `.state/shopify/` (theme deploys may), address I2 first.
