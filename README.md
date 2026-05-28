# ecom-ai-toolkit

Python ops scripts + Claude Code skills for managing a Shopify-centric ecommerce stack.

## Status

v0.1.0 — Foundations + Shopify auth. Future plans (catalog, commerce, storefront, webhooks) are documented under `docs/superpowers/plans/`.

## Install — first 5 minutes

```bash
# 1. clone + sync
git clone https://github.com/aludvigsson/ecom-ai-toolkit && cd ecom-ai-toolkit
uv sync --extra shopify          # or --extra all when other domains land

# 2. run the interactive setup
uv run shopify/scripts/setup.py
# Prompts for store details, then offers two auth paths:
#   - custom-app token (paste from Shopify admin; never expires; best for unattended)
#   - Shopify CLI browser OAuth (token expires in ~24h; best for interactive use)
# Writes store-config.yaml + .env.local, then verifies with a whoami call.

# 3. (optional) install the plugin in Claude Code so skills auto-load
# Inside the repo:
#   claude
# Then ask: "verify my Shopify connection"
```

### Manual setup (fallback)

If you'd rather not use the interactive script:

```bash
cp store-config.example.yaml store-config.yaml
cp .env.example .env.local
# Edit both with your store's domain, locale, and Admin API token.
uv run shopify/scripts/whoami.py
# Expect: shop name, primary domain, plan printed.
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
