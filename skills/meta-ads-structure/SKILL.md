---
name: meta-ads-structure
description: Read and manage Meta (Facebook/Instagram) Ads account structure via the accounts/, campaigns/, adsets/, ads/, and creatives/ CLI scripts. Use when the user says list ad accounts, show my Meta campaigns, get a campaign, list ad sets, list ads, show ad creatives, inspect Meta account structure, create a Meta campaign, create an ad set, create an ad, pause campaign, activate campaign, delete ad set, change campaign budget, or create an ad creative. Reads honor --account-id (normalized to act_<id>), --fields for field selection, --limit pagination, --output table|json|markdown, and --api-version. Writes are safe by default: every create makes a PAUSED entity, activate.py is the only script that sets status=ACTIVE and is --yes-gated, delete and budget changes are --yes-gated, and --dry-run on every write prints the Graph request and exits without calling the API. Conversions API and catalog management are out of scope — use the Graph API directly.
---

# meta-ads-structure

## When to use

- **List ad accounts**: "list ad accounts", "what Meta accounts can I see", "show the accounts under my business".
- **Get an ad account**: "get account act_123", "show details for this ad account".
- **List campaigns**: "show my Meta campaigns", "list campaigns in account act_123", filter by effective status.
- **Get a campaign**: "get campaign 6012345", "show this campaign's objective and budget".
- **List ad sets**: "list ad sets", "show ad sets under this campaign / account".
- **Get an ad set**: "get ad set 6098765", "show this ad set's optimization goal".
- **List ads**: "list ads", "show ads under this ad set / account".
- **Get an ad**: "get ad 6055555", "show this ad's creative".
- **Show ad creatives**: "show ad creatives", "list creatives for this account", "get creative 6077777".
- **Inspect Meta account structure**: walk account → campaigns → ad sets → ads → creatives.

## When NOT to use

- **Performance metrics** (spend, ROAS, impressions, breakdowns) — use the `meta-ads-insights` skill.
- **Conversions API (CAPI) event ingestion** and **catalog / product-feed management** — out of scope; use the Graph API directly.
- **Asset *production*** (writing copy, generating images/video) — out of scope here. This skill wires an *existing* creative's `object_story_spec` into Meta; produce the assets elsewhere.

## Prerequisites

- `META_ACCESS_TOKEN` is set in the environment (read at client construction). If a script returns an auth-shaped error, stop and confirm the token.
- The Graph API version comes from `domains.meta_ads.api_version` in `store-config.yaml`, falling back to the client default; override per call with `--api-version`.
- `--account-id` accepts the id with or without the `act_` prefix; it is normalized to `act_<id>` before the request.
- Install deps: `uv sync --extra meta-ads`.

Common flags from `meta_ads.utils.cli`: `--output table|json|markdown`, `--limit` (cursor pagination cap), `--fields` (comma-separated Graph fields), `--api-version`, `--config`, `--verbose`.

## Account scripts

### List ad accounts

```bash
uv run meta_ads/scripts/accounts/list.py
uv run meta_ads/scripts/accounts/list.py --business-id 123456789   # owned_ad_accounts of a business
```

Parent resolution: `--business-id`, else the `META_BUSINESS_ID` secret, else `me/adaccounts`.

### Get one ad account

```bash
uv run meta_ads/scripts/accounts/get.py --account-id act_123456789
uv run meta_ads/scripts/accounts/get.py --account-id 123456789      # act_ prefix added for you
```

## Campaign scripts

### List campaigns

```bash
uv run meta_ads/scripts/campaigns/list.py --account-id act_123
uv run meta_ads/scripts/campaigns/list.py --account-id act_123 --status ACTIVE   # effective_status filter
```

`--account-id` is required. `--status` filters by `effective_status` (e.g. `ACTIVE`, `PAUSED`, `ARCHIVED`).

### Get one campaign

```bash
uv run meta_ads/scripts/campaigns/get.py --id 6012345
```

## Ad set scripts

### List ad sets

```bash
uv run meta_ads/scripts/adsets/list.py --account-id act_123
uv run meta_ads/scripts/adsets/list.py --campaign-id 6012345
```

Exactly one parent is required: `--account-id` (all ad sets in the account) or `--campaign-id` (ad sets under one campaign).

### Get one ad set

```bash
uv run meta_ads/scripts/adsets/get.py --id 6098765
```

## Ad scripts

### List ads

```bash
uv run meta_ads/scripts/ads/list.py --account-id act_123
uv run meta_ads/scripts/ads/list.py --adset-id 6098765
```

Exactly one parent is required: `--account-id` (all ads in the account) or `--adset-id` (ads under one ad set).

### Get one ad

```bash
uv run meta_ads/scripts/ads/get.py --id 6055555
```

## Creative scripts

### List ad creatives

```bash
uv run meta_ads/scripts/creatives/list.py --account-id act_123
```

`--account-id` is required (GET `/act_<id>/adcreatives`).

### Get one ad creative

```bash
uv run meta_ads/scripts/creatives/get.py --id 6077777
```

## Writes — safety posture (read this first)

Writes follow a deliberate safe-default + gating design so nothing spends by accident:

- **Every `create` makes a `PAUSED` entity.** There is no flag that creates
  something `ACTIVE` — `status` is hard-coded to `PAUSED` on `campaigns/`,
  `adsets/`, and `ads/` create. This is a guardrail against accidental ad spend.
- **`activate.py` is the only script that sets `status=ACTIVE`**, and it is
  **`--yes`-gated**. To turn an entity on you must run `activate.py --yes`
  explicitly; nothing else can flip an entity live.
- **`delete.py` is `--yes`-gated** (DELETE is irreversible). On `update.py`, a
  **budget change** (`--daily-budget`/`--lifetime-budget`) is **`--yes`-gated**;
  a name-only or status-only update is not.
- **`--dry-run` on every write** prints the Graph node/edge + form params (or the
  `DELETE` intent) and exits `0` **without calling the API**. `--dry-run` is
  honored even on `--yes`-gated scripts and needs no `--yes`, since it touches
  nothing.
- **Budgets and bids are in the account's minor units** (e.g. cents):
  `--daily-budget 5000` is 50.00 in the account currency.
- **Targeting and object-story specs are passed as JSON strings**
  (`--targeting '{...}'`, `--object-story-spec '{...}'`).

Each object family has the same verb set:
`create` / `update` / `pause` / `activate` / `delete` for `campaigns/`,
`adsets/`, and `ads/`; `creatives/` has `create` (plus the read `list`/`get`).
`pause.py` (status → `PAUSED`) is a low-risk flip and is **not** gated.

## Campaign writes

```bash
# Create — always PAUSED; no flag yields ACTIVE
uv run meta_ads/scripts/campaigns/create.py --account-id act_123 \
  --name "Spring Sale" --objective OUTCOME_SALES \
  --daily-budget 5000 --special-ad-categories HOUSING   # repeatable
# Update — name-only is ungated; budget change needs --yes
uv run meta_ads/scripts/campaigns/update.py --id 6012345 --name "Spring Sale v2"
uv run meta_ads/scripts/campaigns/update.py --id 6012345 --daily-budget 8000 --yes
# Pause (ungated) / Activate (--yes-gated, the only ACTIVE write)
uv run meta_ads/scripts/campaigns/pause.py --id 6012345
uv run meta_ads/scripts/campaigns/activate.py --id 6012345 --yes
# Delete (--yes-gated, irreversible)
uv run meta_ads/scripts/campaigns/delete.py --id 6012345 --yes
# Preview any write without touching the API
uv run meta_ads/scripts/campaigns/create.py --account-id act_123 \
  --name x --objective OUTCOME_TRAFFIC --dry-run
```

`create` requires `--name` and `--objective`; optional `--buying-type`,
`--daily-budget`/`--lifetime-budget` (minor units), and repeatable
`--special-ad-categories`. `update --status` accepts only `PAUSED`/`ARCHIVED`
(use `pause.py`/`activate.py` for live flips).

## Ad set writes

```bash
# Create — always PAUSED
uv run meta_ads/scripts/adsets/create.py --account-id act_123 \
  --campaign-id 6012345 --name "Lookalike 1%" \
  --billing-event IMPRESSIONS --optimization-goal LINK_CLICKS \
  --targeting '{"geo_locations":{"countries":["SE"]}}' \
  --daily-budget 3000
uv run meta_ads/scripts/adsets/update.py --id 6098765 --lifetime-budget 50000 --yes
uv run meta_ads/scripts/adsets/pause.py --id 6098765
uv run meta_ads/scripts/adsets/activate.py --id 6098765 --yes
uv run meta_ads/scripts/adsets/delete.py --id 6098765 --yes
```

`create` requires `--account-id`, `--campaign-id`, `--name`, `--billing-event`,
`--optimization-goal`, and `--targeting` (JSON string); optional
`--daily-budget`/`--lifetime-budget`/`--bid-amount` (minor units) and
`--start-time`/`--end-time` (ISO 8601).

## Ad writes

```bash
# Create — always PAUSED; wires an existing creative by id
uv run meta_ads/scripts/ads/create.py --account-id act_123 \
  --adset-id 6098765 --name "Hero ad" --creative-id 6077777
uv run meta_ads/scripts/ads/update.py --id 6055555 --name "Hero ad v2"
uv run meta_ads/scripts/ads/pause.py --id 6055555
uv run meta_ads/scripts/ads/activate.py --id 6055555 --yes
uv run meta_ads/scripts/ads/delete.py --id 6055555 --yes
```

`create` requires `--account-id`, `--adset-id`, `--name`, and `--creative-id`
(an existing ad creative). The creative is passed as `{"creative_id": ...}`.

## Creative writes

```bash
# Create an ad creative from an object story spec (JSON string)
uv run meta_ads/scripts/creatives/create.py --account-id act_123 \
  --name "Spring hero creative" \
  --object-story-spec '{"page_id":"123","link_data":{"link":"https://example.com","message":"Shop now"}}'
```

`create` requires `--account-id`, `--name`, and `--object-story-spec` (validated
as JSON before the call). Produce the underlying copy/images/video elsewhere —
this script only registers the spec with Meta.

## Reference

For Conversions API (CAPI), catalog / product-feed management, and anything not
exposed by these scripts, use the Meta Graph API directly. Asset *production*
(copywriting, image/video generation) is out of scope — these scripts wire
existing assets into the account structure.
