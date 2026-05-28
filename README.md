# ecom-ai-toolkit

Python ops scripts + Claude Code skills for managing a Shopify-centric ecommerce stack.

## Status

v0.1.0 — Foundations + Shopify auth. See `docs/superpowers/plans/` for the implementation roadmap.

## Install

```bash
git clone https://github.com/aludvigsson/ecom-ai-toolkit
cd ecom-ai-toolkit
uv sync --extra shopify              # or --extra all
cp store-config.example.yaml store-config.yaml
cp .env.example .env.local
# Fill in store-config.yaml and .env.local
uv run shopify/scripts/whoami.py
```

## Documentation

- Spec: `docs/superpowers/specs/`
- Plans: `docs/superpowers/plans/`
- Per-domain: `docs/<domain>/` (added in later plans)

## License

MIT
