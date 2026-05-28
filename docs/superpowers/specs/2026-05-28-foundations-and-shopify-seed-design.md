# ecom-ai-toolkit — Foundations & Shopify Seed (v1 Design)

**Status:** Draft for review
**Date:** 2026-05-28
**Scope:** v1 only — repo foundations plus the Shopify domain built end-to-end as the reference implementation. Klaviyo, Meta Ads, Google Ads, Microsoft Ads, Google Merchant Center, and Google Tag Manager are explicit follow-up specs that slot into the foundation defined here.

---

## 1. Purpose

`ecom-ai-toolkit` is a portable Claude Code plugin **and** a Python monorepo for managing a Shopify-centric ecommerce stack. It exists to give any Shopify store one place where:

- All cross-platform ops automation lives (Shopify, Klaviyo, ad platforms, feeds, tagging).
- Claude Code can drive that automation through skills that wrap small, focused Python scripts.
- A new consumer can clone the repo, fill in a config file and a secrets file, and start managing their store via natural language.

The repo is publishable to GitHub; nothing in `core/`, `shopify/`, or any other domain folder is store-specific. Per-store specifics live in `store-config.yaml` and `.env.local`, both of which the consumer authors.

---

## 2. Non-goals

- Replacing the Shopify Admin UI or any platform's native UI.
- Hosting a multi-tenant service. The toolkit is a per-store install.
- Editing Hydrogen storefront source code. Hydrogen is a separate React/Remix codebase; this toolkit only offers Hydrogen-aware URL helpers.
- Deploying the optional webhook receiver. The receiver is shipped as runnable code; deployment is the consumer's concern.
- Using any MCP server at runtime. All platform calls happen in Python.

---

## 3. Architecture

Three conceptual layers:

1. **Knowledge layer** — `Shopify/Shopify-AI-Toolkit`, declared as a plugin dependency in `.claude-plugin/plugin.json`. Provides skills like `shopify-plugin:shopify-admin` that document the Admin GraphQL schema. Claude consults these when writing/explaining GraphQL operations. The toolkit does not vendor or fork it.
2. **Ops layer (Python)** — per-domain folders (`shopify/`, `klaviyo/`, `meta_ads/`, …) holding `scripts/` and `utils/client.py`. Scripts are the unit of work: each one is invoked from the command line via `uv run <path>` with `argparse` flags. No MCP calls. Every script imports from `core/` for config/secrets/state/http.
3. **Orchestration layer (skills)** — thin `SKILL.md` files under `skills/<name>/`. A skill tells Claude *when* the workflow applies and *how* to invoke the underlying Python scripts. Skills do not contain implementation; they reference scripts.

### Why this split

- The knowledge layer (Shopify-AI-Toolkit) changes on Shopify's release cycle and is heavy reference text. Keeping it as a dependency avoids merge debt and keeps our skill files short.
- The ops layer must be deterministic, testable, and runnable outside Claude Code. Python scripts + `argparse` satisfy all three.
- The orchestration layer is where natural-language triggers, prerequisites, common pitfalls, and worked examples live — the things Claude needs to make good decisions about which script to run.

---

## 4. Repo layout

```
ecom-ai-toolkit/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── skills/                              # flat, one folder per skill, kebab-case
│   ├── shopify-auth/SKILL.md
│   ├── shopify-products/SKILL.md
│   ├── shopify-orders/SKILL.md
│   ├── shopify-customers/SKILL.md
│   ├── shopify-metafields/SKILL.md
│   ├── shopify-translations/SKILL.md
│   ├── shopify-discounts/SKILL.md
│   ├── shopify-collections/SKILL.md
│   ├── shopify-inventory/SKILL.md
│   ├── shopify-webhooks/SKILL.md
│   ├── shopify-theme/SKILL.md
│   └── shopify-hydrogen/SKILL.md
├── core/                                # snake_case Python module
│   ├── __init__.py
│   ├── config.py
│   ├── secrets.py
│   ├── state.py
│   ├── http.py
│   └── logging.py
├── shopify/                             # snake_case domain folder
│   ├── scripts/                         # see § 6 for full listing
│   ├── utils/
│   │   └── client.py
│   └── README.md
├── klaviyo/                             # placeholder, populated in follow-up spec
├── meta_ads/
├── google_ads/
├── microsoft_ads/
├── merchant_center/
├── gtm/
├── docs/
│   ├── superpowers/specs/               # design docs, including this file
│   └── shopify/                         # per-domain reference + recipes
├── tests/
│   ├── core/                            # unit, no network
│   └── shopify/                         # integration, env-gated
├── workspace/                           # scratch space for Claude/user, gitignored
├── .state/                              # per-domain idempotency files, gitignored
├── pyproject.toml                       # uv-managed
├── uv.lock
├── store-config.example.yaml
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── README.md
├── CHANGELOG.md
└── LICENSE
```

**Folder naming convention:** Python import paths require underscores (`meta_ads/`); skill folders are kebab-case (`meta-ads-cli/`) per Claude Code convention.

---

## 5. Core conventions

These are the contracts every domain follows. Adding the 10th platform must be mechanically the same as adding the 1st.

### 5.1 `store-config.yaml`

Per-store, **committed by the consumer** (not by us). Loaded by `core.config.load_config()` into a typed dataclass (or `pydantic` model — decision deferred to plan).

```yaml
store:
  name: "Example Store"
  primary_domain: example.com
  shopify_domain: example-store.myshopify.com
  storefront_type: hydrogen            # "hydrogen" | "online_store_2"
  default_locale: sv-SE

markets:
  - code: se
    name: Sverige
    locale: sv-SE
    currency: SEK
    url_prefix: /se
  - code: de
    locale: de-DE
    currency: EUR
    url_prefix: /de

domains:
  shopify:    { enabled: true, api_version: "2025-10" }
  klaviyo:    { enabled: false }
  meta_ads:   { enabled: false }
  google_ads: { enabled: false }
  microsoft_ads: { enabled: false }
  merchant_center: { enabled: false }
  gtm:        { enabled: false }
```

Per-market platform IDs (e.g. `google_ads_customer_id`, `meta_ad_account_id`, `klaviyo_list_id`) are added to each `markets[].` block when those domains are enabled in their follow-up specs.

### 5.2 `.env.local`

Per-store, **gitignored**, prefix-namespaced. `.env.example` is committed.

```
# Shopify
SHOPIFY_ADMIN_ACCESS_TOKEN=shpat_***
SHOPIFY_STOREFRONT_ACCESS_TOKEN=
SHOPIFY_WEBHOOK_SECRET=                  # for the optional receiver

# Reserved namespaces for follow-up specs
KLAVIYO_PRIVATE_API_KEY=
META_ACCESS_TOKEN=
META_BUSINESS_ID=
GOOGLE_ADS_DEVELOPER_TOKEN=
GOOGLE_ADS_CLIENT_ID=
GOOGLE_ADS_CLIENT_SECRET=
GOOGLE_ADS_REFRESH_TOKEN=
GOOGLE_ADS_LOGIN_CUSTOMER_ID=
MICROSOFT_ADS_DEVELOPER_TOKEN=
MICROSOFT_ADS_CLIENT_ID=
MICROSOFT_ADS_REFRESH_TOKEN=
GOOGLE_MERCHANT_ACCOUNT_ID=
GOOGLE_TAG_MANAGER_ACCOUNT_ID=
```

`core.secrets.require_secret(name)` fails fast with a message like *"Missing SHOPIFY_ADMIN_ACCESS_TOKEN in .env.local — see .env.example"*. `core.secrets.get_secret(name)` returns `None` if absent.

### 5.3 `.state/<domain>/<task>.json`

Idempotency + audit trail — a `*_state.json` file per long-running or destructive operation.

```
.state/
  shopify/
    bulk_prices_2026-05-28.json
    bulk_op_<id>.json
  meta_ads/
    archive_se_meta_campaign_state.json
```

`core.state.save(domain, name, data: dict)` writes atomically (`tmp` + `os.replace`). `core.state.load(domain, name) -> dict | None`. Always JSON. Always under `.state/`. Always gitignored.

### 5.4 `core/http.py`

A single `HttpClient` (built on `httpx.Client`) with:
- Retries on `429` and `5xx` with exponential backoff + jitter.
- Honors `Retry-After` and Shopify's `X-Shopify-Shop-Api-Call-Limit` (`extensions.cost` for GraphQL).
- Structured one-line logs per request (method, host, path, status, ms, retry count). Auth headers redacted.
- Subclassed by each domain's `utils/client.py`. Nothing in `scripts/` may import `httpx` directly.

### 5.5 `core/logging.py`

Configures stdlib `logging` with a consistent format used by every script. Default level `INFO`, raised to `DEBUG` with `--verbose`. Logs go to stderr; script output (JSON, tables, markdown) goes to stdout — so scripts compose with shell pipes.

### 5.6 `core/__init__.py` public surface

```python
from core.config   import load_config, StoreConfig, Market
from core.secrets  import get_secret, require_secret
from core.state    import load_state, save_state
from core.http     import HttpClient
from core.logging  import get_logger
```

That is the entire public surface of `core/`. Domains that need anything else add it to their own `utils/`, never to `core/`.

### 5.7 Per-domain `utils/client.py` contract

Each domain ships a class that:
- Accepts `(config: StoreConfig, secrets: SecretsProvider)` in `__init__`.
- Subclasses `core.http.HttpClient` (or composes one internally).
- Exposes API-specific high-level methods (`shopify.graphql(query, vars)`, `shopify.bulk_query(query)`, …).
- Is the only thing scripts in that domain import for network access.

---

## 6. Shopify seed — what is built in v1

This is the reference implementation. Every later platform follows the same shape.

### 6.1 Scripts

```
shopify/scripts/
├── whoami.py
├── products/
│   ├── list.py
│   ├── get.py
│   ├── update.py
│   └── bulk_prices.py
├── orders/
│   ├── list.py
│   └── report.py
├── customers/
│   └── list.py
├── metafields/
│   ├── list.py
│   └── set.py
├── metaobjects/
│   ├── list.py
│   ├── upsert.py
│   └── delete.py
├── translations/
│   ├── list.py
│   └── register.py
├── discounts/
│   ├── list.py
│   ├── create.py
│   ├── update.py
│   └── delete.py
├── collections/
│   ├── list.py
│   ├── create.py
│   ├── update.py
│   └── add_products.py
├── inventory/
│   ├── levels.py
│   └── set.py
├── webhooks/
│   ├── list.py
│   ├── create.py
│   ├── delete.py
│   └── receiver/                       # see § 6.3
│       ├── app.py
│       ├── hmac.py
│       ├── handlers/
│       ├── Dockerfile
│       └── README.md
├── theme/
│   ├── list.py
│   ├── get_asset.py
│   └── update_asset.py
└── hydrogen/
    ├── build_variant_url.py
    └── validate_url.py
```

### 6.2 Script conventions (every script in the repo follows these)

- `argparse` with consistent flag names across scripts:
  - `--market <code>` (when applicable) — resolves to a `Market` from `store-config.yaml`.
  - `--dry-run` — read path executes fully; no writes.
  - `--output {table,json,markdown}` — default `table`.
  - `--limit N` — caps result set for reads.
  - `--verbose` — DEBUG logging.
- Imports:
  ```python
  from core.config import load_config
  from core.logging import get_logger
  from shopify.utils.client import ShopifyClient
  ```
- Exits non-zero on any unhandled error; prints a clear error message to stderr.
- Long-running or destructive scripts write a state file to `.state/shopify/<task>_<timestamp>.json` and accept `--resume <state-file>` to continue.

### 6.3 Webhook receiver — boundaries

Shipped as **runnable code, not a deployed service**:
- FastAPI app at `shopify/scripts/webhooks/receiver/app.py`.
- HMAC SHA256 validation against `SHOPIFY_WEBHOOK_SECRET` per Shopify spec, applied via middleware/dependency to every endpoint.
- One handler stub per common topic in `handlers/` (e.g. `orders_create.py`, `orders_updated.py`, `products_update.py`, `app_uninstalled.py`).
- `Dockerfile` plus a `README.md` covering local run (`uv run uvicorn shopify.scripts.webhooks.receiver.app:app`) and deployment hints (Cloud Run / Fly / Render). The toolkit does not provide deploy automation.
- Shares config and secrets with the rest of the toolkit via `core/`.

### 6.4 Hydrogen — boundaries

**In scope:** Pure-Python helpers operating against a Hydrogen storefront URL — variant URL builder, URL validation (HEAD request). These exist because bare Shopify handles do not resolve on Hydrogen storefronts; variant slugs are required.

**Out of scope:** Editing Hydrogen source, Remix routes, components, deploys. Those live in the consumer's Hydrogen repository.

### 6.5 `shopify/utils/client.py`

Methods:
- `.graphql(query: str, variables: dict | None = None) -> dict`
- `.bulk_query(query: str) -> Iterator[dict]` — Shopify Bulk Operations API for large reads (returns JSONL rows).
- `.bulk_mutation(jsonl_path: Path) -> dict` — Bulk Operations for large writes.
- Built-in cost-aware throttling using `extensions.cost.throttleStatus` from each GraphQL response.

### 6.6 Skills (v1)

| Skill | Wraps |
|---|---|
| `shopify-auth` | `whoami.py` + first-time setup walkthrough |
| `shopify-products` | `products/*` |
| `shopify-orders` | `orders/*` |
| `shopify-customers` | `customers/*` |
| `shopify-metafields` | `metafields/*` + `metaobjects/*` |
| `shopify-translations` | `translations/*` |
| `shopify-discounts` | `discounts/*` |
| `shopify-collections` | `collections/*` |
| `shopify-inventory` | `inventory/*` |
| `shopify-webhooks` | `webhooks/*` CRUD + receiver setup doc |
| `shopify-theme` | `theme/*` (OS 2.0 only) |
| `shopify-hydrogen` | `hydrogen/*` |

Every `SKILL.md` follows this structure:

```markdown
---
name: shopify-<area>
description: <natural-language triggers + one-line capability summary>
---
# When to use
# When NOT to use (delegate to other skills)
# Prerequisites (auth check via uv run shopify/scripts/whoami.py)
# Canonical workflows (3-5 worked examples with the exact uv run commands)
# Common pitfalls
# Reference: shopify-plugin:shopify-admin for full GraphQL schema
```

---

## 7. Extension pattern (how Klaviyo / Meta / etc. plug in later)

Adding a new platform is mechanical. Each follow-up spec executes these steps:

1. Add domain folder `<platform>/` with `scripts/` and `utils/client.py`.
2. Build `<platform>/utils/client.py` on top of `core.http.HttpClient`. Accept `StoreConfig` and a secrets provider in `__init__`.
3. Add the platform's secrets prefix to `.env.example` (already reserved in § 5.2).
4. Add a domain config block to `store-config.example.yaml` under `domains.<platform>`; add per-market fields to each `markets[]` entry as needed.
5. Add an optional-deps group in `pyproject.toml` (e.g. `klaviyo = ["klaviyo-api>=..."]`).
6. Add skills under `skills/<platform>-<task>/SKILL.md`.
7. Add docs under `docs/<platform>/`.
8. Add tests under `tests/<platform>/`, gated by `<PLATFORM>_INTEGRATION_TESTS=1`.

**A new platform never edits `core/`.** If it needs `core/` changes, those changes get their own design review.

---

## 8. Packaging

### 8.1 `pyproject.toml`

`uv`-managed. Python 3.12+. Optional dependency groups so consumers install only what they use:

```toml
[project.optional-dependencies]
shopify         = ["httpx>=0.27", "pyyaml>=6", "pydantic>=2"]
klaviyo         = ["klaviyo-api>=..."]
meta-ads        = ["facebook-business>=..."]
google-ads      = ["google-ads>=25"]
microsoft-ads   = ["bingads>=..."]
merchant-center = ["google-api-python-client>=..."]
gtm             = ["google-api-python-client>=..."]
webhooks        = ["fastapi>=0.115", "uvicorn[standard]>=..."]
all             = [<every key above flattened>]
dev             = ["pytest>=8", "ruff>=0.6", "pre-commit>=3"]
```

Install patterns:
- `uv sync --extra shopify` — Shopify-only consumer.
- `uv sync --extra all` — full toolkit.
- `uv sync --extra shopify --extra klaviyo --extra webhooks` — pick-your-own.

### 8.2 `.claude-plugin/plugin.json`

```json
{
  "name": "ecom-ai-toolkit",
  "version": "0.1.0",
  "description": "Python ops scripts + skills for Shopify-centric ecommerce stacks",
  "dependencies": {
    "Shopify/Shopify-AI-Toolkit": "^1.0.0"
  },
  "skills": "./skills"
}
```

### 8.3 `.claude-plugin/marketplace.json`

Standard marketplace entry so the plugin is `/plugin install`-able directly from the GitHub repo URL.

---

## 9. Testing

- `tests/core/` — unit, no network. Covers config loading, secrets loading, state read/write atomicity, HTTP retry/backoff/redaction logic.
- `tests/shopify/` — integration tests gated by `SHOPIFY_INTEGRATION_TESTS=1`, run against a development shop whose credentials are in CI secrets. Cover `whoami`, list endpoints, and dry-run paths of write endpoints.
- `tests/shopify/receiver/` — FastAPI `TestClient` tests with fixture HMAC signatures (no real Shopify needed).
- Every write script implements `--dry-run` exercising the full read path.

CI (GitHub Actions): `ruff check`, `ruff format --check`, `pytest tests/core/`. Integration tests are env-gated and do not run without secrets configured.

---

## 10. Onboarding (a new consumer's first 5 minutes)

`README.md` walks through:

1. `git clone https://github.com/<owner>/ecom-ai-toolkit && cd ecom-ai-toolkit`
2. `uv sync --extra shopify` (or `--extra all`)
3. `cp store-config.example.yaml store-config.yaml` and fill in
4. `cp .env.example .env.local` and fill in (minimum: `SHOPIFY_ADMIN_ACCESS_TOKEN`)
5. `uv run shopify/scripts/whoami.py` — must print the shop name
6. Launch Claude Code in this directory (plugin auto-loads). Ask: *"List my 10 most recent products."*
7. README also documents installing the plugin globally via `/plugin install <repo-url>` so it works outside the repo directory.

---

## 11. Repo hygiene

- `.gitignore`: `.env.local`, `.env.local.*`, `.state/`, `workspace/`, `__pycache__/`, `*.egg-info`, `.venv/`, `.pytest_cache/`, `.ruff_cache/`.
- `ruff` for lint + format. Config in `pyproject.toml`.
- `pytest` config in `pyproject.toml`.
- `.pre-commit-config.yaml`: `ruff check --fix`, `ruff format`, secret-scan (e.g. `gitleaks`).
- `LICENSE`: MIT.
- `CHANGELOG.md`: keep-a-changelog format, starting at `0.1.0`.
- GitHub Actions on push: lint + `tests/core/`. Integration tests do not run in CI without secrets.

---

## 12. Open questions for the implementation plan

These are deferred to the writing-plans step, not blockers for design approval:

- **Config schema validator:** `dataclasses + manual validation` vs `pydantic`. Pydantic adds a dep but gives clean errors. Lean: pydantic, since `shopify` extra already needs it for typed responses.
- **GraphQL query storage:** inline string literals in scripts, vs `.graphql` files loaded at import time, vs a generated client. Lean: inline literals for v1; revisit if duplication grows.
- **Logging format:** plain text (human-friendly) vs JSON (machine-friendly). Lean: plain by default, `--log-json` flag for JSON.
- **Test shop:** does the user have a Shopify development store available for integration tests, or do we provide instructions for spinning one up via the Partners dashboard?

---

## 13. Out of scope for v1 (will be follow-up specs)

- Klaviyo
- Meta Ads
- Google Ads
- Microsoft Ads
- Google Merchant Center
- Google Tag Manager
- Any other domain not listed in § 6

Each follow-up spec executes the § 7 extension pattern.
