# Plan 2 — Deferred concerns (v0.2.0-alpha → v0.2.0 final / Plan 3 prerequisites)

Findings from the final Plan 2 whole-plan code review. None blocked v0.2.0-alpha; the items below should be addressed before Plans 3-5 cargo-cult the patterns into ~30 more scripts.

## Important (land before Plan 3 starts)

### I1. `--market` and `--verbose` are dead flags
**Where:** `shopify/utils/cli.py:add_common_flags` registers `--market` and `--verbose` but `grep -rn "args.market\|args.verbose" shopify/scripts/` returns zero hits across all 15 Plan 2 scripts.

**Why:** Documented-vs-behavior lie. Plan 3 (orders/inventory) genuinely needs market scoping — every orders query and inventory level operates per-location-per-market.

**Fix:**
- Wire `args.market` through `load_config(args.config, market=args.market)` in every script (this requires extending `load_config` to accept a market parameter and use it as the default market context for any market-aware operations).
- Wire `args.verbose` to raise the logger level: `if args.verbose: logging.getLogger("ecom").setLevel(logging.DEBUG)`.
- Alternatively: remove both from `add_common_flags` and re-add per-script where actually used. The wire-through approach is preferable since Plan 3 will need it everywhere.

### I2. State files have no `schema_version`
**Where:** `shopify/scripts/products/bulk_prices.py` writes `{started_at, csv_path, sku_to_variant_id, completed_variant_ids, variant_to_product}` to `.state/shopify/bulk_prices_<ts>.json` with no version marker.

**Why:** Plan 3 will add bulk_inventory, bulk_discounts, bulk_customer_imports state files. When the bulk_prices schema evolves (failed_chunks, retry_count, etc.), `_load_resume` will silently accept stale-shape files and crash later with confusing errors.

**Fix:**
- Add `"schema_version": 1` to fresh state dicts in `bulk_prices.py`.
- `_load_resume` raises a clear `StateSchemaError` (or similar) when version is missing or higher than supported.
- Standardize this in `core.state.save_state(domain, name, data)` so future state writers get it automatically (add a `schema_version` kwarg, default 1).

### I3. `AmbiguousSkuError` and `SkuNotFoundError` are stranded in `bulk_prices.py`
**Where:** Both defined as module-level classes in `shopify/scripts/products/bulk_prices.py`.

**Why:** Plan 3 inventory + discount scripts will need the same SKU-resolution pattern. Keeping them in `bulk_prices.py` means Plan 3 either redefines them divergently or imports from a deeply-nested script module.

**Fix:**
- Move both to `shopify/utils/client.py` (or a new `shopify/utils/lookup.py` if growing).
- Update `bulk_prices.py` to import them.
- Document `RuntimeError` as the base for input-data conditions vs `LookupError` for stdlib-aligned "not found" patterns. Pick one rule.

### I4. CSV validation uses bare `RuntimeError` in translations/register.py
**Where:** `shopify/scripts/translations/register.py` validation raises bare `RuntimeError` when a row is missing the digest column.

**Why:** Other Plan 2 validation uses typed exceptions (`AmbiguousSkuError`, `ShopifyUserError`). For consistency CSV-validation errors should also be typed and ideally subclass `ValueError` (stdlib convention for malformed input).

**Fix:** Define `TranslationCsvValidationError(ValueError)` in the script (or in shared utils if Plan 3 needs the same pattern), use it. While we're at it, codify a convention: malformed input → `ValueError` subclass; API-response anomaly → `RuntimeError` subclass.

## Suggestions

### S1. Chunk-boundary test gap
**Where:** `bulk_prices.py` (250 chunks), `metafields/set.py` (25 chunks), `collections/add_products.py` (250 chunks).

**Why:** No test exercises the 250+1 or 25+1 boundary. A 251-item input should produce two graphql calls of 250 + 1; a 250-item input should produce one. Currently chunking is implicitly trusted. Webhooks replay (Plan 5) will compound any chunker bug.

**Fix:** Add three parametrized tests (one per script) verifying the boundary behavior.

### S2. CHANGELOG `0.2.0` entry is accurate but understated
**Where:** `CHANGELOG.md`.

**Why:** Does not mention (a) the new typed exceptions `AmbiguousSkuError`/`SkuNotFoundError`, (b) the `--yes`-gating convention on `metaobjects/delete.py` (worth advertising — Plan 3's `orders/cancel.py` will reuse it), (c) the state-file schema for `bulk_prices`.

**Fix:** Add a "Conventions" sub-section to the changelog entry so Plans 3-5 can reference it.

### S3. `shopify-metafields` skill bundles two domains
**Where:** `skills/shopify-metafields/SKILL.md` covers both metafields and metaobjects.

**Why:** When Plan 5 adds `shopify-webhooks` the trigger phrases may overlap ("custom data" / "webhook payload metafield").

**Fix:** Consider splitting into `shopify-metafields` + `shopify-metaobjects` before Plan 3 doubles the skill catalog. Low priority — current setup works.

### S4. Bare exception swallowing in `_persist_state`
**Where:** `bulk_prices.py:_persist_state` has `except Exception: pass`.

**Why:** Silently swallowing exceptions on the state-save path defeats the resumability story.

**Fix:** At minimum log via `_log.warning("falling back to direct write: %s", exc)`. Better: name the specific exception expected.

### S5. `--limit` is meaningless on write scripts
**Where:** `add_common_flags` registers `--limit` default 50 for ALL scripts; mutation scripts (`update.py`, `set.py`, `delete.py`, `register.py`) silently accept and discard it.

**Why:** Same problem as I1 — flag documentation vs behavior diverges.

**Fix:** Either drop `--limit` from `add_common_flags` and add per-list-script, or document it explicitly as "no-op on write scripts."

---

## How to address

- Items I1, I2, I3 (Important): one polish PR before Plan 3 starts. ~1-2 hours.
- Item I4 + S2 (Important + cheap): fold into the same polish PR.
- Items S1, S4, S5: opportunistic cleanup during early Plan 3 batches.
- Item S3: re-evaluate before Plan 5.
