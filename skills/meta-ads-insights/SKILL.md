---
name: meta-ads-insights
description: Pull Meta (Facebook/Instagram) Ads performance via the insights/query CLI script. Use when the user says Meta ads performance, campaign insights, ad spend report, ROAS by campaign, breakdown by age and gender, or insights for the last 30 days. Reads metrics at --level account|campaign|adset|ad for an --account-id (normalized to act_<id>) or any --object-id, over a --date-preset or a --since/--until range, with optional --breakdowns and --fields, honoring --limit and --output table|json|markdown. Read-only.
---

# meta-ads-insights

## When to use

- **Account/campaign/ad performance**: "Meta ads performance", "how are my Facebook ads doing", "spend and ROAS this month".
- **Campaign insights**: "campaign insights", "metrics per campaign", "which campaign spent the most".
- **Ad spend report**: "ad spend report", "total spend last 30 days", "CPM and CTR by ad set".
- **ROAS by campaign**: "ROAS by campaign", "return on ad spend per campaign / ad set".
- **Segmented reporting**: "breakdown by age and gender", "performance by placement / country".
- **Time-bounded reporting**: "insights for the last 30 days", "spend between two dates".

## When NOT to use

- **Structure reads** (accounts, campaigns, ad sets, ads, creatives) — use the `meta-ads-structure` skill.
- **Writes** of any kind — deferred to Plan M2. This skill is read-only.
- **Conversions API event ingestion** and **catalog management** — out of scope; use the Graph API directly.

## Prerequisites

- `META_ACCESS_TOKEN` is set in the environment (read at client construction). If the script returns an auth-shaped error, stop and confirm the token.
- The Graph API version comes from `domains.meta_ads.api_version` in `store-config.yaml`, falling back to the client default; override with `--api-version`.
- `--account-id` accepts the id with or without the `act_` prefix; it is normalized to `act_<id>` before the request.
- Install deps: `uv sync --extra meta-ads`.

Common flags from `meta_ads.utils.cli`: `--output table|json|markdown`, `--limit` (cursor pagination cap), `--fields` (comma-separated metrics), `--api-version`, `--config`, `--verbose`.

## insights/query

```bash
# Account-level, default last 30 days
uv run meta_ads/scripts/insights/query.py --account-id act_123

# Campaign-level rows for an account
uv run meta_ads/scripts/insights/query.py --account-id act_123 --level campaign

# Insights for a specific campaign/adset/ad node
uv run meta_ads/scripts/insights/query.py --object-id 6012345 --level campaign

# Explicit date range (since/until together)
uv run meta_ads/scripts/insights/query.py --account-id act_123 --since 2026-05-01 --until 2026-05-28

# Breakdown by age and gender
uv run meta_ads/scripts/insights/query.py --account-id act_123 --breakdowns age,gender

# Custom field selection, JSON output
uv run meta_ads/scripts/insights/query.py --account-id act_123 --fields spend,impressions,ctr,cpc --output json
```

### Flags

- `--level {account,campaign,adset,ad}` — aggregation level of the returned rows (default `account`).
- **Object selection** — exactly one of:
  - `--account-id` — the insights node is `act_<id>`.
  - `--object-id` — any campaign / ad set / ad node id to pull insights for.
- **Time window** — `--date-preset` (default `last_30d`) **or** `--since`/`--until` (`YYYY-MM-DD`, supplied together). The two are mutually exclusive; a range overrides the preset.
- `--breakdowns` — comma-separated Graph breakdowns (e.g. `age,gender`, `country`, `publisher_platform`).
- `--fields` — comma-separated metrics; defaults to a spend/reach/clicks/CPC/CPM/CTR/frequency/actions set.
- `--limit` / `--output` — page cap and `table|json|markdown` rendering, per the shared conventions above.

Insights rows are already flat metric dicts, so each row is emitted as-is.

## Reference

For structure reads use `meta-ads-structure`. For writes use Plan M2's skill
once it ships. For Conversions API and catalog management, use the Meta Graph
API directly.
