---
name: shopify-translations
description: Read translatable content + existing translations and bulk-register new translations via the translations/ CLI scripts. Use when the user says list translations for product/collection/etc., register translations from CSV, translate a metafield into a target locale, or sweep all translations of a resource type in a market. Honors --dry-run.
---

# shopify-translations

Shopify translations are attached per-`(resource_id, locale, key)` and are versioned via a `translatableContentDigest` that pins each translation to a specific snapshot of the source. The standard workflow is: `list.py` to fetch source values + digests for a resource (or sweep a whole resource type), send those to a translator (or LLM) to produce translated values, then `register.py` to push the translations back via `translationsRegister`. Supported `--resource-type` values include `PRODUCT`, `PRODUCT_VARIANT`, `COLLECTION`, `SHOP`, `EMAIL_TEMPLATE`, `SHOP_POLICY`, `LINK`, and `METAFIELD`.

## When to use

- User wants to **list translations** for one resource at a locale: "list translations for product", "show me Swedish translations for collection", "what translations exist on this email template in German".
- User wants to **sweep translations** across a whole resource type: "find all product translations missing in DE", "list every collection translation in fi-FI", "sweep email-template translations".
- User wants to **bulk-register translations** from a CSV: "register translations from CSV", "translate products into German", "upload translated metafield values".
- User wants to **translate a single metafield** into a target locale by hand: list the metafield's translatable content + digest, edit the value, register one CSV row.
- User wants the **export-translate-import loop**: list to JSON, translate offline, re-shape into CSV, register.

## When NOT to use

- User wants to change a market's currency or locale **settings** (not the content translations) — that's `shopify-markets` (future skill).
- User wants to fetch translatable content **without** the existing translations alongside — these scripts always return both together; use `shopify-plugin:shopify-admin` directly if you need a different query shape.
- User wants **mass machine translation** — this skill writes translations, it doesn't generate them. Generate translated values upstream (LLM, Google Translate, professional translator), then pipe results through `register.py`.
- Auth not working / "is my shop connected?" → delegate to `shopify-auth`.

## Prerequisites

- `shopify-auth` has been run successfully **OR** `store-config.yaml` and `.env.local` exist at repo root with `SHOPIFY_ADMIN_ACCESS_TOKEN` populated.
- Project deps installed: `uv sync --extra shopify`.
- For any `register.py` run, every CSV row needs a `translatable_content_digest` value captured via a fresh `list.py` call. The digest is Shopify's freshness check — without it, the registration is rejected.

If any script in this skill returns an auth-shaped error, stop and delegate to `shopify-auth`.

## Canonical workflows

### 1. List translatable content + existing translations for one product in Swedish

```bash
uv run shopify/scripts/translations/list.py \
  --resource-id gid://shopify/Product/12345 \
  --locale sv-SE \
  --output json
```

Returns both the source `translatableContent` (with `digest` per key) and the existing `translations` at `sv-SE`. JSON output is the right format when the next step is `register.py`, because the digests round-trip cleanly.

### 2. Sweep all product translations in German

```bash
uv run shopify/scripts/translations/list.py \
  --resource-type PRODUCT \
  --locale de-DE \
  --limit 50
```

Sweep mode walks `translatableResources(resourceType: PRODUCT)` and reports source + existing translations for each. Table output is convenient here for eyeballing gaps; switch to `--output json` if you're piping into a translator.

### 3. Export-translate-register loop

1. List the source content + digests, dump to JSON:
   ```bash
   uv run shopify/scripts/translations/list.py \
     --resource-type PRODUCT --locale sv-SE --limit 100 \
     --output json > products_sv.json
   ```
2. Translate offline. Produce a CSV with these exact columns (one row per translatable key per resource per locale):
   ```
   resource_id,locale,key,value,translatable_content_digest
   gid://shopify/Product/12345,sv-SE,title,Höstjacka,d41d8cd98f00...
   gid://shopify/Product/12345,sv-SE,body_html,<p>Varm och vattentät.</p>,a52f9b...
   ```
3. Dry-run, then register for real:
   ```bash
   uv run shopify/scripts/translations/register.py --from-csv translations.csv --dry-run
   uv run shopify/scripts/translations/register.py --from-csv translations.csv
   ```

### 4. Register a small batch from CSV

```bash
uv run shopify/scripts/translations/register.py --from-csv my_translations.csv
```

The script groups rows by `resource_id` and calls `translationsRegister` once per resource group. Errors surface via `userErrors` on the mutation response.

### 5. Translate a single metafield value

```bash
# Step 1: find the digest for the metafield's translatable key
uv run shopify/scripts/translations/list.py \
  --resource-id gid://shopify/Metafield/98765 \
  --locale de-DE \
  --output json
# Step 2: hand-craft a one-row CSV with that digest + your translation, then register.
```

`METAFIELD` is a valid `--resource-type` for sweep mode too, if you want to translate many metafield values at once.

## Common pitfalls

- **`translatable_content_digest` is REQUIRED on every CSV row.** Empty cells fail validation in `register.py` with a row-number error before any API call. If the source content has changed since the digest was captured, Shopify rejects the registration with a `userErrors` digest-mismatch — refetch via `list.py` and re-run.
- **Keys are Shopify-defined per resource type.** For products, common keys include `title`, `body_html`, `meta_title`, `meta_description`, and `product_type`. For collections, `title`, `body_html`, `meta_title`, `meta_description`. For metafields, the key is the metafield's value-translation key. Always list the resource first to see the exact keys available — do not guess.
- **Sweep mode is paginated by `--limit` and does not auto-follow `endCursor`.** `list.py` exposes `pageInfo { hasNextPage endCursor }` in the underlying query but does not currently chain calls. For catalogs larger than your `--limit`, either raise `--limit` (Shopify caps `first` at 250) or call repeatedly with different filters until coverage is sufficient.
- **Locale strings must match Shopify's published-locale list exactly.** Typically `xx` or `xx-YY` (e.g. `sv`, `sv-SE`, `de`, `de-DE`, `nb`, `nb-NO`). Case matters: `sv-se` is not the same as `sv-SE`. Locales the shop hasn't published are rejected by the mutation.
- **You cannot translate a resource into its primary locale.** Shopify rejects this at the mutation level. `list.py` will still return the source `translatableContent.value` for the primary locale (because that's the source itself) — treat those values as untranslatable, not as a translation to round-trip.
- **`register.py` does not chunk inside a single resource group.** Each `resource_id` group is sent as one `translationsRegister` call; very large per-resource batches (e.g. hundreds of translatable keys on one product, which is unusual) may approach Shopify's per-mutation size limits. In practice, one resource has a handful of keys, so this rarely matters.
- **CSV column names are exact.** `resource_id`, `locale`, `key`, `value`, `translatable_content_digest`. The header row must match — typos cause the row-validation step to fail on row 1.

## Reference

For the full Admin GraphQL schema — the `translatableResource` and `translatableResources` queries, the complete `TranslatableResourceType` enum (every valid value for `--resource-type`), the `translationsRegister` mutation, `TranslationInput` shape, and the `translatableContentDigest` semantics — defer to `shopify-plugin:shopify-admin` from the Shopify-AI-Toolkit plugin dependency.
