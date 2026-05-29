# Klaviyo domain — design spec

**Status:** Approved for planning (2026-05-29)
**Scope:** The `klaviyo/` domain built end-to-end on the v1 foundation, following the §7 extension pattern from the foundations spec (`docs/superpowers/specs/2026-05-28-foundations-and-shopify-seed-design.md`). The Shopify domain is the reference implementation; this spec mirrors its conventions.
**Depends on:** v1 foundation (`core/`, the `klaviyo` reserved extra, `KLAVIYO_PRIVATE_API_KEY`, `domains.klaviyo` config block). No `core/` changes.

---

## 1. Goal

Ship full-CRUD command-line management of a Klaviyo account across four capability clusters — audience (profiles/lists/segments), sending (campaigns/templates), and reporting (flows/metrics) — with the same UX, safety, and testing conventions as the Shopify domain. Every script is `uv run klaviyo/scripts/<cluster>/<op>.py` with `argparse` flags; no MCP calls; built on `core.http.HttpClient`.

## 2. Non-goals / boundaries

- **No vendor SDK.** Uses Klaviyo's raw JSON:API over `httpx` via `core.http`, exactly as the Shopify domain uses raw GraphQL. The `klaviyo` extra therefore needs only the same base deps as `shopify` (`httpx`, `pyyaml`, `pydantic`); no `klaviyo-api` dependency.
- **No segment definition authoring in v1.** Creating/updating segments requires Klaviyo's condition DSL; v1 ships `segments/{list,get}` (and member listing) only. Segment create/update is deferred.
- **No MCP.** A Klaviyo MCP server may exist in some environments; the toolkit deliberately does not call it (foundations spec §2).
- **Deployment / scheduling of the scripts** is the consumer's concern (cron, CI, etc.).

## 3. Architecture

```
klaviyo/
  __init__.py
  utils/
    __init__.py
    client.py      # KlaviyoClient on core.http.HttpClient
    cli.py         # add_common_flags / configure_logging_from_args / format_output
  scripts/
    __init__.py
    profiles/   lists/   segments/      # Plan K1 (audience)
    campaigns/  templates/              # Plan K2 (sending)
    flows/      metrics/                # Plan K3 (reporting)
```

### 3.1 `klaviyo/utils/client.py`

`KlaviyoClient(config: StoreConfig)`:

- Reads `KLAVIYO_PRIVATE_API_KEY` via `core.secrets.require_secret` at construction (mirrors `ShopifyClient`).
- Base URL `https://a.klaviyo.com/api/`.
- Default headers:
  - `Authorization: Klaviyo-API-Key <key>`
  - `revision: <revision>` — required dated revision. Default from `config.domains["klaviyo"].revision`, falling back to a module constant `_DEFAULT_REVISION` (a known-good dated revision); overridable per-invocation via a `--revision` flag plumbed into the client.
  - `accept: application/vnd.api+json`, `content-type: application/vnd.api+json`
- Methods:
  - `get(path, params=None)`, `post(path, json=None)`, `patch(path, json=None)`, `delete(path)` — thin wrappers over `core.http.HttpClient` (which already exposes `.get/.post/.patch/.delete` and retries on 429/5xx with backoff). Each returns the parsed JSON body (or `None`/`{}` for `204` deletes).
  - `paginate(path, params=None)` → `Iterator[dict]` — yields `data[]` items across pages by following `links.next` (cursor pagination). Respects a `--limit` cap and an `--all` opt-out of the cap (see §4).
- Error handling: a module-level `check_errors(body)` raises `KlaviyoAPIError` when the JSON:API response carries a non-empty top-level `errors[]` array, summarizing `errors[].detail` (and `source.pointer` when present), analogous to Shopify's `check_user_errors`. Auth failures (`401`) surface a message pointing at `KLAVIYO_PRIVATE_API_KEY`.
- Context-manager (`__enter__/__exit__/close`) closing the underlying `HttpClient`, mirroring `ShopifyClient`.

Exceptions defined here: `KlaviyoAPIError(RuntimeError)` (carries `.errors` and optional parsed `.body`). Add `ProfileNotFoundError`/`ResourceNotFoundError(LookupError)` if a lookup-by-email/by-id pattern needs a typed not-found (decision deferred to plan, mirroring Shopify's `SkuNotFoundError`).

### 3.2 `klaviyo/utils/cli.py`

A near-copy of `shopify/utils/cli.py`: `add_common_flags` (`--dry-run`, `--output {table,json,markdown}`, `--limit`, `--config`, `--verbose`), `configure_logging_from_args`, `format_output` (table/json/markdown). Duplicated rather than imported from `shopify/` to avoid coupling two domains. **Deferred follow-up (needs its own `core/` review):** promote these shared CLI helpers to `core/cli.py` so domains share one implementation. Tracked, not done here.

The `klaviyo` scripts additionally register `--revision` (client revision override) via a small `add_klaviyo_flags` helper, and high-stakes ops register `--yes`.

## 4. Conventions (identical to Shopify domain)

- One script = one operation. `main(argv=None) -> int`, `if __name__ == "__main__": sys.exit(main())`, the `sys.path` bootstrap block for direct `uv run` execution.
- `--dry-run` on every mutation prints the JSON:API request body it *would* send and returns `0` without calling the API.
- `--yes` gates high-stakes operations: campaign `schedule`, campaign `cancel`, campaign `delete`, list `delete`, list `remove_profiles`, profile `unsubscribe`, flow `update_status`. `--dry-run` works without `--yes`; live execution of a gated op requires `--yes` (mirrors `webhooks/delete.py` and `discounts/delete.py`).
- `--limit` default 50; `--all` follows pagination to completion (logs a notice when truncating at `--limit`).
- Output flattens JSON:API resources (`{id, type, attributes:{…}}`) into flat rows (`id`, plus selected attributes) for readable tables, same spirit as `webhooks/list.py`'s endpoint flattening.

## 5. Script inventory

### K1 — audience
| Script | API | Notes |
|---|---|---|
| `profiles/list.py` | `GET /profiles` | filters: `--email`, `--list-id`, `--segment-id`; pagination |
| `profiles/get.py` | `GET /profiles/{id}` or by `--email` | by id or email lookup |
| `profiles/create.py` | `POST /profiles` | `--dry-run` |
| `profiles/update.py` | `PATCH /profiles/{id}` | `--dry-run` |
| `profiles/subscribe.py` | `POST /profile-subscription-bulk-create-jobs` | consent; `--dry-run` |
| `profiles/unsubscribe.py` | `POST /profile-subscription-bulk-delete-jobs` | `--dry-run`, `--yes` |
| `lists/list.py` | `GET /lists` | |
| `lists/get.py` | `GET /lists/{id}` (+ `/profiles`) | `--with-members` |
| `lists/create.py` | `POST /lists` | `--dry-run` |
| `lists/update.py` | `PATCH /lists/{id}` | `--dry-run` |
| `lists/delete.py` | `DELETE /lists/{id}` | `--dry-run`, `--yes` |
| `lists/add_profiles.py` | `POST /lists/{id}/relationships/profiles` | `--dry-run` |
| `lists/remove_profiles.py` | `DELETE /lists/{id}/relationships/profiles` | `--dry-run`, `--yes` |
| `segments/list.py` | `GET /segments` | |
| `segments/get.py` | `GET /segments/{id}` (+ `/profiles`) | `--with-members` |

### K2 — sending
| Script | API | Notes |
|---|---|---|
| `campaigns/list.py` | `GET /campaigns` | requires the `messages.channel` filter Klaviyo mandates; default `email` |
| `campaigns/get.py` | `GET /campaigns/{id}` | |
| `campaigns/create.py` | `POST /campaigns` | `--dry-run` |
| `campaigns/schedule.py` | `POST /campaign-send-jobs` (or schedule attr) | `--dry-run`, `--yes` (highest stakes) |
| `campaigns/cancel.py` | `PATCH`/cancel job | `--dry-run`, `--yes` |
| `campaigns/delete.py` | `DELETE /campaigns/{id}` | `--dry-run`, `--yes` |
| `templates/list.py` | `GET /templates` | |
| `templates/get.py` | `GET /templates/{id}` | |
| `templates/create.py` | `POST /templates` | `--dry-run` |
| `templates/update.py` | `PATCH /templates/{id}` | `--dry-run` |
| `templates/delete.py` | `DELETE /templates/{id}` | `--dry-run`, `--yes` |
| `templates/render.py` | `POST /template-render` | render with context |
| `templates/clone.py` | `POST /template-clone` | |
| `templates/assign.py` | `POST /campaign-message-assign-template` | assign template to a campaign message |

### K3 — reporting
| Script | API | Notes |
|---|---|---|
| `flows/list.py` | `GET /flows` | |
| `flows/get.py` | `GET /flows/{id}` (+ flow-actions/messages) | |
| `flows/update_status.py` | `PATCH /flows/{id}` (status) | activate/deactivate; `--dry-run`, `--yes` |
| `metrics/list.py` | `GET /metrics` | |
| `metrics/get.py` | `GET /metrics/{id}` | |
| `metrics/aggregate.py` | `POST /metric-aggregates` | metric aggregate query |
| `events/list.py` | `GET /events` | filters by metric/profile/time |
| `events/create.py` | `POST /events` | track an event; low risk |
| `reports/campaign.py` | `POST /campaign-values-reports` | campaign performance |
| `reports/flow.py` | `POST /flow-values-reports` | flow performance |

## 6. Data flow

`parse_args` → `configure_logging_from_args` → `load_config(args.config)` → `KlaviyoClient(config)` (reads secret) → build request (reads for queries; JSON:API body for mutations) → `--dry-run` prints body and returns `0`, else call → `check_errors(body)` → flatten → `print(format_output(rows, args.output))` → `return 0`.

## 7. Error handling

- JSON:API `errors[]` → `KlaviyoAPIError` with concatenated `detail` (+ `source.pointer`).
- `401` → message naming `KLAVIYO_PRIVATE_API_KEY`; suggest re-checking `.env.local`.
- `429` → handled by `core.http` retry/backoff (honors `Retry-After`).
- Missing/invalid `revision` → defaulted by the client; `--revision` overrides.
- Gated op without `--yes` and without `--dry-run` → `parser.error(...)` before any network call.

## 8. Testing

- **Unit:** `tests/klaviyo/utils/test_client.py` mocks `core.http.HttpClient` responses (auth header, revision header, pagination follow, `check_errors`, 204 delete). Per-script tests under `tests/klaviyo/scripts/test_<cluster>_<op>.py` mock `KlaviyoClient` methods and assert: request shape (JSON:API body for mutations), `--dry-run` skips the call, gated ops require `--yes`, output rendering for table/json.
- **Integration:** `tests/klaviyo/test_*_integration.py` gated by `KLAVIYO_INTEGRATION_TESTS=1`, skipped by default and in CI.
- **CI:** add `--extra klaviyo` to the sync step; the existing `pytest tests/` run picks up `tests/klaviyo/`.

## 9. Config & secrets

- `.env.example` already reserves `KLAVIYO_PRIVATE_API_KEY` (no change needed beyond documenting it's now active).
- `store-config.example.yaml`: extend `domains.klaviyo` to `{ enabled: false, revision: "<dated>" }`.
- Per-market: `klaviyo_list_id` (and similar) added to `markets[]` entries as scripts need them.

## 10. Skills (§7 step 6)

`skills/klaviyo-profiles/`, `klaviyo-lists` (or folded into profiles), `klaviyo-campaigns`, `klaviyo-templates`, `klaviyo-flows`, `klaviyo-metrics` — each documenting its cluster's scripts, the `--dry-run`/`--yes` posture, and deferring advanced/unsupported operations to direct API use. Final skill grouping decided per plan.

## 11. Implementation split (for writing-plans)

- **Plan K1 — foundation + audience:** `klaviyo/utils/{client,cli}.py`, config/secret wiring, `profiles/*`, `lists/*`, `segments/{list,get}`, unit tests, CI `--extra klaviyo`, `klaviyo-profiles`/`klaviyo-lists` skills. Deliverable: manage audience from the CLI.
- **Plan K2 — sending:** `campaigns/*`, `templates/*`, tests, `klaviyo-campaigns`/`klaviyo-templates` skills. Deliverable: build/schedule campaigns (gated).
- **Plan K3 — reporting:** `flows/*`, `metrics/*`, `events/*`, `reports/*`, tests, `klaviyo-flows`/`klaviyo-metrics` skills. Deliverable: reporting + flow control.

## 12. Definition of done (domain-level)

- `uv sync --extra klaviyo` installs and all `klaviyo/scripts/*` run.
- Full CRUD across the four clusters per §5, with `--dry-run` on all mutations and `--yes` on the high-stakes set.
- `KlaviyoClient` unit-tested (auth, revision, pagination, error surfacing).
- Per-script unit tests green; integration tests gated and skipped by default.
- CI installs `--extra klaviyo` and runs `tests/klaviyo/`.
- Skills cover each cluster. CHANGELOG bumped per plan; domain tagged when K3 lands.
