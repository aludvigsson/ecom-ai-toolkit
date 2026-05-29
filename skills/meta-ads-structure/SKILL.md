---
name: meta-ads-structure
description: Read Meta (Facebook/Instagram) Ads account structure via the accounts/, campaigns/, adsets/, ads/, and creatives/ CLI scripts. Use when the user says list ad accounts, show my Meta campaigns, get a campaign, list ad sets, list ads, show ad creatives, or inspect Meta account structure. Every script is read-only here and honors --account-id (normalized to act_<id>), --fields for field selection, --limit pagination, --output table|json|markdown, and --api-version. Create, update, pause, activate, and delete are deferred to Plan M2; Conversions API and catalog management are out of scope — use the Graph API directly.
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

- **Writes** — create, update, pause, activate, and delete of campaigns/ad sets/ads/creatives are **deferred to Plan M2**. This skill ships **read-only** here. When the writes land in M2 they default new objects to `PAUSED` (the safe-default-`PAUSED` rule) so nothing spends before review.
- **Performance metrics** (spend, ROAS, impressions, breakdowns) — use the `meta-ads-insights` skill.
- **Conversions API (CAPI) event ingestion** and **catalog / product-feed management** — out of scope; use the Graph API directly.

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

## Reference

For writes (create/update/pause/activate/delete), use Plan M2's skill once it
ships (safe default: new objects start `PAUSED`). For Conversions API, catalog
management, and anything not exposed by these read scripts, use the Meta Graph
API directly.
