# ecom-ai-toolkit

Python ops scripts + Claude Code skills for managing a Shopify-centric ecommerce stack.

## Status

v0.1.0 — Foundations + Shopify auth. Future plans (catalog, commerce, storefront, webhooks) are documented under `docs/superpowers/plans/`.

## Install — first 5 minutes

```bash
# 1. clone + sync
git clone https://github.com/aludvigsson/ecom-ai-toolkit && cd ecom-ai-toolkit
uv sync --extra shopify          # or --extra all when other domains land

# 2. fill in per-store config (gitignored)
cp store-config.example.yaml store-config.yaml
cp .env.example .env.local
# Edit both with your store's domain, locale, and Admin API token.

# 3. verify auth
uv run shopify/scripts/whoami.py
# Expect: shop name, primary domain, plan printed.

# 4. (optional) install the plugin in Claude Code so skills auto-load
# Inside the repo:
#   claude
# Then ask: "verify my Shopify connection"
```

## Repo layout

```
core/                  # Shared library: config, secrets, state, http, logging
shopify/               # Shopify domain: utils/client.py + scripts/
skills/                # Claude Code skills (kebab-case)
.claude-plugin/        # Plugin manifest (depends on Shopify/Shopify-AI-Toolkit)
docs/superpowers/      # Specs + plans
tests/                 # core/ unit tests + per-domain integration tests
```

## Adding a domain (future plans)

See `docs/superpowers/specs/2026-05-28-foundations-and-shopify-seed-design.md` § 7 ("Extension pattern").

## License

MIT
