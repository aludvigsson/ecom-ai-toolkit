---
name: shopify-auth
description: Verify Shopify Admin API authentication for the current store and walk a new user through first-time setup. Use when the user says the toolkit isn't working, gets an auth error, or asks "is my Shopify connected?". Also runs as the very first thing on a fresh install before any other Shopify skill.
---

# shopify-auth

## When to use

- New install: user has just cloned the repo and needs to verify their setup before doing anything else.
- Any Shopify script fails with an auth-shaped error (`MissingSecretError`, 401, "Invalid API key or access token").
- User explicitly asks: "is my shop connected?" / "test my Shopify creds" / "whoami".

## When NOT to use

- The user has a real Shopify question (products, orders, etc.). Delegate to the appropriate Shopify skill (`shopify-products`, `shopify-orders`, …). Don't pre-emptively run whoami on every request.

## Prerequisites

- `store-config.yaml` exists at repo root and has `store.shopify_domain` set.
- `.env.local` exists at repo root and has `SHOPIFY_ADMIN_ACCESS_TOKEN` set.
- Project deps installed: `uv sync --extra shopify`.

If either of the files above is missing, walk the user through copying the `.example` versions and filling them in. Do NOT proceed to running whoami until they confirm both files exist.

## Canonical workflow

```bash
uv run shopify/scripts/whoami.py
```

Expected output:
```
Shop:    <Store name>
Domain:  https://<their-domain>
Plan:    <Shopify plan>
```

If the user wants JSON: `uv run shopify/scripts/whoami.py --output json`.

## Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `MissingSecretError: SHOPIFY_ADMIN_ACCESS_TOKEN` | `.env.local` missing or token unset | Copy `.env.example` to `.env.local`, fill in token |
| `FileNotFoundError: store-config not found` | First-time install hasn't been completed | Copy `store-config.example.yaml` to `store-config.yaml` and fill in |
| `ShopifyGraphQLError: Invalid API key or access token` | Token wrong scope or expired | Regenerate token in Shopify admin: Settings → Apps → Develop apps → your app → API credentials. Token must be a custom-app *Admin API access token*, not a Storefront token. |
| `401` with no GraphQL error | Wrong header — likely using Storefront token | Confirm it's a token starting with `shpat_` (Admin API), not `shpsst_` (Storefront) |

## Reference

For full Admin API schema and capability questions, defer to the `shopify-plugin:shopify-admin` skill from the Shopify-AI-Toolkit plugin dependency.
