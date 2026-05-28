# ecom-ai-toolkit — v1 Implementation Plans

The v1 spec (`docs/superpowers/specs/2026-05-28-foundations-and-shopify-seed-design.md`) is split into five plans, each producing working, testable software on its own.

| # | Plan | Depends on | What's deliverable when done |
|---|---|---|---|
| 1 | [Foundations + Shopify auth](2026-05-28-plan-1-foundations-and-shopify-auth.md) | (none) | Plugin installs; `uv run shopify/scripts/whoami.py` prints shop info; `core/` covered by unit tests; CI green |
| 2 | [Shopify catalog](2026-05-28-plan-2-shopify-catalog.md) | 1 | Products, collections, metafields, metaobjects, translations |
| 3 | [Shopify commerce](2026-05-28-plan-3-shopify-commerce.md) | 1 | Orders, customers, inventory, discounts |
| 4 | [Shopify storefront](2026-05-28-plan-4-shopify-storefront.md) | 1 | Theme (OS 2.0) + Hydrogen URL helpers |
| 5 | [Shopify webhooks](2026-05-28-plan-5-shopify-webhooks.md) | 1 | Webhook CRUD + FastAPI receiver |

**Execution order:** Plan 1 must ship first. Plans 2–5 are independent and can be done in any order, sequentially or in parallel branches.

**Plans 2–5 caveat:** Their detail leans on contracts locked in by Plan 1. If Plan 1's `core/` API surface or the `ShopifyClient` shape change during execution, re-read plans 2–5 and update before starting them.
