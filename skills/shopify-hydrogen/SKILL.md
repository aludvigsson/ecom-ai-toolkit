---
name: shopify-hydrogen
description: Build canonical Hydrogen variant URLs and HEAD-check storefront URLs via the hydrogen/ CLI scripts. Use when the user says build variant URL for product X in market Y, validate Hydrogen URLs, what's the URL for SKU Z in DE, check storefront URLs are live, URLs broken on storefront, or Hydrogen URL helpers. Pure-Python — no Shopify Admin API required. Honors --output table|json|markdown.
---

# shopify-hydrogen

## When to use

- User wants to **build a canonical variant URL** for a product on a Hydrogen storefront: "what's the URL for `pearl-classic` variant 12345 in the DE market?", "give me the variant URL for SKU `PRL-100` on the Norwegian site", "build the link for this product/variant combo".
- User wants to **HEAD-check storefront URLs**: "are these Hydrogen URLs still live?", "validate this list of variant URLs", "did any of these 404 after the last deploy?", "check storefront URLs are not broken".
- User wants to **generate URLs in bulk** for a feed, email, or campaign and then verify each one resolves.

## When NOT to use

- **Editing Hydrogen source code** — those edits live in your separate React/Remix Hydrogen repo. This skill only generates and validates URLs.
- **Online Store 2.0 storefronts** — `build_variant_url.py` errors if `storefront_type: online_store_2`. Use the bare Shopify URL pattern `https://<domain>/products/<handle>?variant=<id>` directly.
- **Shopify Admin queries** (read product, variant, inventory, metafields) — delegate to other `shopify-*` skills.
- **True variant-existence checks** — `validate_url.py` only confirms HTTP < 400 on the storefront. A Hydrogen page with `?variant=99999999` (non-existent variant) typically returns 200 anyway. Query the Admin API to confirm a variant actually exists.

## Prerequisites

- `store-config.yaml` with `store.storefront_type: hydrogen` set, plus `store.primary_domain` and `markets[*].url_prefix`.
- No Shopify Admin API token needed — these scripts are pure-local URL construction + HEAD requests against the public storefront.
- Project deps installed: `uv sync --extra shopify`.

## How the scripts split

- **`build_variant_url.py` constructs the URL.** Reads `store-config.yaml`, picks the market (explicit `--market` or default from `store.default_locale`), and writes `https://<domain><market.url_prefix>/products/<handle>?variant=<id>` (or `?sku=<sku>`). Pure local; no network.
- **`validate_url.py` HEAD-checks URLs.** Accepts `--url` (repeatable) or `--from-csv` with a `url` column. Follows redirects and reports the final URL. Exit 1 if any URL returns >= 400.

## Canonical workflows

### 1. Build a variant URL by ID for the Swedish market

```bash
uv run shopify/scripts/hydrogen/build_variant_url.py \
  --handle pearl-classic \
  --variant-id 42949672960123 \
  --market se
```

### 2. Build by SKU instead (variant ID may be unknown)

```bash
uv run shopify/scripts/hydrogen/build_variant_url.py \
  --handle pearl-classic \
  --variant-sku PRL-100 \
  --market de
```

### 3. Build for the default market (skip `--market`)

The script picks the market whose `locale` matches `store.default_locale`.

```bash
uv run shopify/scripts/hydrogen/build_variant_url.py \
  --handle pearl-classic \
  --variant-id 12345
```

### 4. JSON output for piping into a feed or downstream script

```bash
uv run shopify/scripts/hydrogen/build_variant_url.py \
  --handle pearl-classic \
  --variant-id 12345 \
  --market se \
  --output json
```

### 5. Validate one URL is live

```bash
uv run shopify/scripts/hydrogen/validate_url.py \
  --url 'https://curaofsweden.com/se/products/pearl-classic?variant=12345'
```

### 6. Bulk validate from CSV

CSV must have a `url` column.

```bash
uv run shopify/scripts/hydrogen/validate_url.py --from-csv urls.csv
```

### 7. Pipeline: build URLs and validate each

```bash
uv run shopify/scripts/hydrogen/build_variant_url.py \
  --handle pearl-classic --variant-id 12345 --market se --output json \
  | jq -r '.url' \
  | xargs -n1 -I {} uv run shopify/scripts/hydrogen/validate_url.py --url {}
```

## Common pitfalls

- **The URL builder is Hydrogen-only.** For Online Store 2.0 storefronts the variant URL is just `https://<domain>/products/<handle>?variant=<id>` (no market prefix). Use that pattern directly instead of running this script.
- **`market.url_prefix` MUST start with `/`** (e.g. `/se`, `/de`). An empty string `""` means the market is the root (no prefix) — valid for single-market setups.
- **`validate_url.py` follows redirects.** If a 301 → final 200 chain is unexpected, the `final_url` column shows where Hydrogen actually routed the request. Useful for catching unintended locale redirects (e.g. `/products/foo` 301-ing to `/se/products/foo`).
- **A 200 does not mean the variant exists.** Hydrogen typically renders the product page with `?variant=99999999` and just falls back to the default variant. `validate_url.py` only proves the URL resolves, not that the variant is valid. For true existence checks query the Admin API.
- **Multi-domain stores aren't handled.** `build_variant_url.py` only knows about `store.primary_domain`. If your Hydrogen storefront serves multiple TLDs (e.g. `curaofsweden.com` and `cura.de`), wrap the script or extend `store-config.yaml` with per-market domains in a follow-up plan.
- **Silent third-party redirects pass as `ok: True`.** If a URL silently redirects to a parked domain or wrong host, `validate_url.py` reports it as healthy but the `final_url` column shows the unexpected host. Always inspect `final_url`, not just `status`.

## Reference

For the official Hydrogen architecture and URL conventions, defer to the `shopify-plugin:shopify-hydrogen` skill. For Storefront API queries that complement these URL helpers (e.g. resolving a SKU to a variant ID before building the URL), defer to `shopify-plugin:shopify-storefront-graphql`.
