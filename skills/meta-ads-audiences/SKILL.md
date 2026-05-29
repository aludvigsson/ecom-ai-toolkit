---
name: meta-ads-audiences
description: List and manage Meta (Facebook/Instagram) custom and lookalike audiences via the audiences/ CLI scripts. Use when the user says list custom audiences, get a custom audience, create a custom audience, create a lookalike audience, add users to an audience, remove users from an audience, upload hashed emails, upload customer list, delete a custom audience, or Meta audience targeting. Every script takes --account-id (normalized to act_<id> where applicable), --output table|json|markdown, and --api-version; reads honor --limit cursor pagination. Identifier privacy is enforced: add_users/remove_users normalize (trim+lowercase) and SHA-256-hash every identifier before transmission — raw values never leave the process and never appear in --dry-run output. Writes are safe by default: every mutation supports --dry-run (prints the Graph request, exits 0), and add_users, remove_users, and delete are --yes-gated (live execution aborts before any network call when --yes is missing). create and create_lookalike are not gated (no identifier/membership write). Conversions API / Pixel event ingestion and catalog/commerce audiences are out of scope — use the Graph API directly.
---

# meta-ads-audiences

## When to use

- **List custom audiences**: "list custom audiences", "show audiences in act_123".
- **Get a custom audience**: "get audience 6012345", "show this audience's size and retention".
- **Create a custom audience**: "create a custom audience", "make an empty customer-list audience".
- **Create a lookalike audience**: "create a lookalike audience", "build a 1% lookalike from this seed".
- **Add users to an audience**: "add users to an audience", "upload hashed emails", "upload this customer list".
- **Remove users from an audience**: "remove users from an audience", "delete these emails from the audience".
- **Delete a custom audience**: "delete a custom audience".
- **Meta audience targeting**: walk the list → get → populate → derive-lookalike flow.

## When NOT to use

- **Conversions API (CAPI) / Pixel event ingestion** — out of scope (spec §2); use the Graph API directly.
- **Catalog / commerce / product-feed audiences** — out of scope; use the Graph API directly.
- **Campaign / ad set / ad / creative structure** — use the `meta-ads-structure` skill.
- **Performance metrics** (spend, ROAS, reach) — use the `meta-ads-insights` skill.

## Prerequisites

- `META_ACCESS_TOKEN` is set in the environment (read at client construction). If a script returns an auth-shaped error, stop and confirm the token.
- The Graph API version comes from `domains.meta_ads.api_version` in `store-config.yaml`, falling back to the client default; override per call with `--api-version`.
- `--account-id` accepts the id with or without the `act_` prefix; it is normalized to `act_<id>` before the request.
- Install deps: `uv sync --extra meta-ads`.

Common flags from `meta_ads.utils.cli`: `--output table|json|markdown`, `--limit` (cursor pagination cap, on reads), `--fields` (comma-separated Graph fields, on reads), `--api-version`, `--config`, `--verbose`.

## Read scripts

### List custom audiences

```bash
uv run meta_ads/scripts/audiences/list.py --account-id act_123
uv run meta_ads/scripts/audiences/list.py --account-id act_123 --limit 100 --output json
```

`--account-id` is required (GET `/act_<id>/customaudiences`). Nodes are flattened
to flat rows (id, name, subtype, approximate count bounds, operation status,
time updated) for table output.

### Get one custom audience

```bash
uv run meta_ads/scripts/audiences/get.py --id 6012345
```

`--id` is required. Returns name, subtype, description, retention days, count
bounds, and operation status.

## Writes — safety posture (read this first)

- **`--dry-run` on every mutation** prints the Graph request (method, path, form
  data / params) and exits `0` **without calling the API**. On `add_users` /
  `remove_users` the printed payload contains only **SHA-256 hashes** — raw
  identifiers never appear.
- **`add_users`, `remove_users`, and `delete` are `--yes`-gated.** Without
  `--yes`, live execution aborts via `parser.error` **before any network call or
  config load**. `--dry-run` is honored without `--yes` (it touches nothing).
- **`create` and `create_lookalike` are not gated** — creating an empty container
  or deriving a lookalike performs no identifier/membership write.

## Create scripts (not gated)

### Create a custom audience (empty container)

```bash
uv run meta_ads/scripts/audiences/create.py --account-id act_123 \
  --name "Newsletter subscribers" \
  --subtype CUSTOM --description "From CRM export" \
  --retention-days 180 --customer-file-source USER_PROVIDED_ONLY
```

POST `/act_<id>/customaudiences`. `--name` is required; `--subtype` defaults to
`CUSTOM`. For `CUSTOM`, Graph requires `--customer-file-source` (default
`USER_PROVIDED_ONLY`; also `PARTNER_PROVIDED_ONLY`,
`BOTH_USER_AND_PARTNER_PROVIDED`). Optional `--description`,
`--retention-days`. Creates an **empty** audience — populate it with `add_users`.

### Create a lookalike audience (derived)

```bash
uv run meta_ads/scripts/audiences/create_lookalike.py --account-id act_123 \
  --name "Lookalike 1% SE" \
  --source-audience-id 6012345 --country SE --ratio 0.01
```

POST `/act_<id>/customaudiences` with `subtype=LOOKALIKE`. Requires
`--account-id`, `--name`, `--source-audience-id` (the seed/origin audience),
`--country`, and `--ratio`. **`--ratio` must be in `(0, 0.2]`** (e.g. `0.01` =
closest 1%); out-of-range aborts via `parser.error`.

## Membership writes (`--yes`-gated, identifier-hashing)

`add_users` and `remove_users` collect identifiers from `--value` (repeatable)
or `--value-file` (one per line). Every identifier is **normalized (trimmed +
lowercased) and SHA-256-hashed** before transmission — raw values never leave
the process and never appear in `--dry-run` output. `--kind email|phone`
(default `email`) selects the `EMAIL_SHA256` / `PHONE_SHA256` schema.

### Add users to an audience

```bash
# Preview first — prints the hashed payload, no --yes needed
uv run meta_ads/scripts/audiences/add_users.py --id 6012345 \
  --kind email --value alice@example.com --value bob@example.com --dry-run
# Live — requires --yes
uv run meta_ads/scripts/audiences/add_users.py --id 6012345 \
  --kind email --value-file emails.txt --yes
```

**Transport:** POST `/<audience_id>/users` with the JSON-encoded `payload`
object (`{"schema": ..., "data": [[<hash>], ...]}`) sent as a **form param**.

### Remove users from an audience

```bash
uv run meta_ads/scripts/audiences/remove_users.py --id 6012345 \
  --kind email --value alice@example.com --dry-run
uv run meta_ads/scripts/audiences/remove_users.py --id 6012345 \
  --kind email --value-file emails.txt --yes
```

**Transport:** `remove_users` issues a **DELETE** on `/<audience_id>/users` with
the same `payload` object sent as a **query/form param — not a JSON body** (spec
note). Same normalization + SHA-256 hashing as `add_users`.

## Delete (`--yes`-gated)

```bash
uv run meta_ads/scripts/audiences/delete.py --id 6012345 --dry-run
uv run meta_ads/scripts/audiences/delete.py --id 6012345 --yes
```

DELETE `/<audience_id>`. Irreversible; `--yes` is required for live execution.

## Reference

For Conversions API (CAPI) / Pixel event ingestion and catalog / commerce
audiences, use the Meta Graph API directly — these are out of this skill's
domain scope (spec §2).
