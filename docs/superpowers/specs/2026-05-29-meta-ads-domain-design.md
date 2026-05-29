# Meta Ads domain — design spec

**Status:** Approved for planning (2026-05-29)
**Scope:** The `meta_ads/` domain built end-to-end on the v1 foundation, following the §7 extension pattern from the foundations spec (`docs/superpowers/specs/2026-05-28-foundations-and-shopify-seed-design.md`). The Shopify domain is the reference for conventions; the Klaviyo domain (`docs/superpowers/specs/2026-05-29-klaviyo-domain-design.md`) is the most recent precedent for a third-party API domain.
**Depends on:** v1 foundation (`core/`, the `meta-ads` reserved extra, `META_ACCESS_TOKEN`/`META_BUSINESS_ID`, `domains.meta_ads` config). No `core/` changes.

---

## 1. Goal

Ship command-line management of a Meta (Facebook/Instagram) Ads account across four clusters — structure reads, structure CRUD, insights/reporting, and audiences — with the same UX, safety, and testing conventions as the Shopify/Klaviyo domains, built on the **Graph API** over `core.http.HttpClient`. Every script is `uv run meta_ads/scripts/<cluster>/<op>.py` with `argparse`; no MCP; no vendor SDK.

## 2. Non-goals / boundaries

- **No `facebook-business` SDK.** Uses the raw Graph API over `httpx` via `core.http`, exactly as Shopify uses raw GraphQL and Klaviyo raw JSON:API. The `meta-ads` extra needs only the base deps (`httpx`, `pyyaml`, `pydantic`).
- **Safe-default writes:** entity `create` scripts always create **`PAUSED`**; there is no "create active" path. Activation is a separate, `--yes`-gated `activate` script. This is a deliberate guardrail against accidental ad spend.
- **No creative *production*** (image/video generation, copy authoring). `creatives/create` wires an existing image hash / page post / link spec into an ad creative object; producing the assets is out of scope.
- **No Conversions API / Pixel events ingestion**, no Commerce/Catalog management — separate concerns (the latter overlaps the Merchant Center follow-up spec).
- **No MCP.**

## 3. Architecture

```
meta_ads/
  __init__.py
  utils/
    __init__.py
    client.py     # MetaClient on core.http.HttpClient (Graph API)
    cli.py        # add_common_flags / add_meta_flags / configure_logging_from_args / format_output
  scripts/
    __init__.py
    accounts/  campaigns/  adsets/  ads/  creatives/   # structure (M1 reads, M2 writes)
    insights/                                          # M1 reporting
    audiences/                                         # M3 targeting
```

### 3.1 `meta_ads/utils/client.py`

`MetaClient(config: StoreConfig)`:

- Reads `META_ACCESS_TOKEN` via `core.secrets.require_secret` at construction.
- Base URL `https://graph.facebook.com/<version>/`. **Version stored in the existing `DomainConfig.api_version`** (e.g. `v21.0`), default from `config.domains["meta_ads"].api_version`, falling back to a module constant `_DEFAULT_VERSION`; overridable via `--api-version`. **No `core/` change** (same approach as Klaviyo's revision).
- Auth: `Authorization: Bearer <token>` header (Graph API also accepts `?access_token=`; the header keeps tokens out of logged URLs).
- `account_path(account_id)` helper normalizes to the `act_<id>` form (accepts id with or without the prefix).
- Methods over `core.http.HttpClient`:
  - `get(path, params=None)`, `post(path, data=None)`, `delete(path, params=None)` — Graph creates/updates are `POST` (updates POST to the node id; deletes are `DELETE` or `POST ?_method=DELETE` — use `DELETE`). Return parsed JSON.
  - `paginate(path, params=None)` → `Iterator[dict]` — yields items from `data[]` across pages by following `paging.next` (absolute URL) / `paging.cursors.after`, respecting `--limit`.
- `fields` selection: helper to pass a comma-joined `fields` param.
- Error handling: module-level `check_error(body)` raises `MetaAPIError` when the response carries a top-level `error` object, surfacing `error.message`, `error.code`, `error.error_subcode`, and `error.fbtrace_id`. `401`/`190` (token) errors point at `META_ACCESS_TOKEN`.
- Context manager closing the underlying `HttpClient`.

Exceptions: `MetaAPIError(RuntimeError)` (carries `code`, `subcode`, `fbtrace_id`, `body`).

### 3.2 `meta_ads/utils/cli.py`

Near-copy of `shopify/utils/cli.py`: `add_common_flags` (`--dry-run`, `--output {table,json,markdown}`, `--limit`, `--config`, `--verbose`), `configure_logging_from_args`, `format_output`. Plus `add_meta_flags` registering `--api-version` and `--yes`. Duplicated to avoid cross-domain coupling; **deferred follow-up (own `core/` review):** promote shared CLI helpers to `core/cli.py`. Tracked, not done here.

## 4. Conventions (identical to Shopify/Klaviyo)

- One script = one operation; `main(argv=None) -> int`; the `sys.path` bootstrap block for direct `uv run`.
- `--dry-run` on every mutation prints the Graph request (node/edge + params) it *would* send and returns `0` without calling the API.
- **Safe-default create:** `create` scripts force `status=PAUSED`; no flag can create an `ACTIVE` entity. `activate` is a separate script, `--yes`-gated.
- `--yes` gates: every `activate`, every `delete`, budget changes on `update` (`--daily-budget`/`--lifetime-budget`), and audience `add_users`/`remove_users`.
- `--limit` default 50; pagination follows `paging.next`.
- Graph nodes flattened into flat rows for table output.

## 5. Script inventory

### M1 — foundation + structure reads + insights
| Script | Graph | Notes |
|---|---|---|
| `accounts/list.py` | `GET /<business_id>/owned_ad_accounts` (or `/me/adaccounts`) | `META_BUSINESS_ID` default |
| `accounts/get.py` | `GET /act_<id>` | field selection |
| `campaigns/list.py` | `GET /act_<id>/campaigns` | `--account-id`, status filter |
| `campaigns/get.py` | `GET /<campaign_id>` | |
| `adsets/list.py` | `GET /act_<id>/adsets` or `/<campaign_id>/adsets` | |
| `adsets/get.py` | `GET /<adset_id>` | |
| `ads/list.py` | `GET /act_<id>/ads` or `/<adset_id>/ads` | |
| `ads/get.py` | `GET /<ad_id>` | |
| `creatives/list.py` | `GET /act_<id>/adcreatives` | |
| `creatives/get.py` | `GET /<creative_id>` | |
| `insights/query.py` | `GET /<object_id>/insights` | `--level {account,campaign,adset,ad}`, `--date-preset` or `--time-range`, `--breakdowns`, `--fields`, `--account-id` |

### M2 — structure CRUD (safe-default + gated)
| Script | Graph | Notes |
|---|---|---|
| `campaigns/create.py` | `POST /act_<id>/campaigns` | forces `status=PAUSED`; `--objective`, `--name`, special-ad-categories; `--dry-run` |
| `campaigns/update.py` | `POST /<campaign_id>` | name/budget; budget change `--yes` |
| `campaigns/pause.py` | `POST /<campaign_id>` `status=PAUSED` | `--dry-run` |
| `campaigns/activate.py` | `POST /<campaign_id>` `status=ACTIVE` | `--dry-run`, `--yes` |
| `campaigns/delete.py` | `DELETE /<campaign_id>` | `--dry-run`, `--yes` |
| `adsets/{create,update,pause,activate,delete}.py` | analogous | create forces PAUSED; targeting/budget/schedule on create |
| `ads/{create,update,pause,activate,delete}.py` | analogous | create forces PAUSED; references a creative |
| `creatives/create.py` | `POST /act_<id>/adcreatives` | wires existing image hash / object story spec; `--dry-run` |

### M3 — audiences
| Script | Graph | Notes |
|---|---|---|
| `audiences/list.py` | `GET /act_<id>/customaudiences` | |
| `audiences/get.py` | `GET /<audience_id>` | |
| `audiences/create.py` | `POST /act_<id>/customaudiences` | custom audience (rule/website/customer-file subtype metadata); `--dry-run` |
| `audiences/create_lookalike.py` | `POST /act_<id>/customaudiences` (`subtype=LOOKALIKE`) | `--source-audience-id`, `--country`, `--ratio`; `--dry-run` |
| `audiences/add_users.py` | `POST /<audience_id>/users` | SHA-256-hashed identifiers in the `payload` form param (schema + data); `--dry-run`, `--yes` |
| `audiences/remove_users.py` | `DELETE /<audience_id>/users` | same `payload` form param (not a JSON body); pass via `params`/form on the DELETE; `--dry-run`, `--yes` |
| `audiences/delete.py` | `DELETE /<audience_id>` | `--dry-run`, `--yes` |

## 6. Data flow

`parse_args` → `configure_logging_from_args` → `load_config` → `MetaClient(config)` (reads token) → build request (params for reads; node/edge + form data for writes) → `--dry-run` prints intent and returns `0`, else call → `check_error(body)` → flatten → `format_output`.

## 7. Error handling

- Graph `error{message,code,error_subcode,fbtrace_id}` → `MetaAPIError` with all fields in the message (fbtrace_id is essential for Meta support).
- Token errors (HTTP 401, code 190) → message naming `META_ACCESS_TOKEN`.
- Rate limiting (code 4/17/80004, HTTP 429) → handled by `core.http` retry/backoff; `MetaClient` notes the `X-Business-Use-Case-Usage` header in `--verbose` logs.
- Gated op without `--yes` (and not `--dry-run`) → `parser.error(...)` before any network call.

## 8. Testing

- **Unit:** `tests/meta_ads/utils/test_client.py` mocks `core.http.HttpClient` (auth/version, `act_` normalization, `paging.next` follow, `check_error`, field selection). Per-script tests under `tests/meta_ads/scripts/test_<cluster>_<op>.py` mock `MetaClient` and assert request shape, that `create` forces `PAUSED`, `--dry-run` skips the call, gated ops require `--yes`, and output rendering.
- **Integration:** `tests/meta_ads/test_*_integration.py` gated by `META_INTEGRATION_TESTS=1`, skipped by default and in CI.
- **CI:** add `--extra meta-ads` to the sync step; existing `pytest tests/` picks up `tests/meta_ads/`.

## 9. Config & secrets

- `.env.example` already reserves `META_ACCESS_TOKEN`, `META_BUSINESS_ID` (document as active).
- `store-config.example.yaml`: set `domains.meta_ads` to `{ enabled: false, api_version: "<vXX.0>" }` — `api_version` holds the Graph API version. **No `core/config.py` change.**
- `pyproject.toml`: populate the `meta-ads` extra with `["httpx>=0.27", "pyyaml>=6", "pydantic>=2.7"]`.
- Per-market: `meta_ad_account_id` added to `markets[]` entries as scripts need them.

## 10. Skills (§7 step 6)

`skills/meta-ads-structure/` (accounts/campaigns/adsets/ads/creatives reads+CRUD), `skills/meta-ads-insights/`, `skills/meta-ads-audiences/` — each documenting its cluster, the safe-default-PAUSED rule, `--dry-run`/`--yes` posture, and deferring unsupported ops (CAPI, catalog) to direct API use. Final grouping decided per plan.

## 11. Implementation split (for writing-plans)

- **Plan M1 — foundation + reads + insights:** `meta_ads/utils/{client,cli}.py`, packaging/config/CI wiring, `accounts/{list,get}`, `campaigns/{list,get}`, `adsets/{list,get}`, `ads/{list,get}`, `creatives/{list,get}`, `insights/query`, unit tests, `meta-ads-structure` (read sections) + `meta-ads-insights` skills. Deliverable: inspect + report on a Meta account.
- **Plan M2 — structure CRUD:** `campaigns/`, `adsets/`, `ads/` create(PAUSED)/update/pause/activate/delete + `creatives/create`, with safe-default + `--yes` gating, tests, complete `meta-ads-structure` skill. Deliverable: manage campaign structure without accidental spend.
- **Plan M3 — audiences:** `audiences/{list,get,create,create_lookalike,add_users,remove_users,delete}`, tests, `meta-ads-audiences` skill, CHANGELOG, domain tag. Deliverable: audience/targeting management.

## 12. Definition of done (domain-level)

- `uv sync --extra meta-ads` installs and all `meta_ads/scripts/*` run.
- Four clusters per §5; `--dry-run` on all mutations; `create` always PAUSED; `--yes` on activate/delete/budget-change/audience-users.
- `MetaClient` unit-tested (auth, version, `act_` normalization, pagination, error surfacing with fbtrace_id).
- Per-script unit tests green; integration tests gated and skipped by default.
- CI installs `--extra meta-ads` and runs `tests/meta_ads/`.
- Skills cover each cluster. CHANGELOG bumped per plan; domain tagged when M3 lands.
