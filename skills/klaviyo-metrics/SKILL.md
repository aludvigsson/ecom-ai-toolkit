---
name: klaviyo-metrics
description: Inspect Klaviyo metrics and pull performance reports via the metrics/ and reports/ CLI scripts. Use when the user says list metrics, show a metric, metric aggregate, how many placed orders, campaign performance report, flow performance report, open rate, click rate, or revenue report. metrics/list and metrics/get are read-only and honor --output table|json|markdown; metrics/aggregate, reports/campaign, and reports/flow are read-style POST queries (no mutation) that still honor --dry-run to preview the JSON:API request body. None of these are --yes-gated. Reports require --conversion-metric-id (the conversion metric, e.g. the Placed Order metric). Anything not exposed here — custom metric definitions, ad-hoc analytics — is deferred to direct Klaviyo API use.
---

# klaviyo-metrics

## When to use

- **List metrics**: "list metrics", "what metrics do I have", "show my Klaviyo metrics".
- **Show a metric**: "show metric abc123", "get the details of the Placed Order metric".
- **Metric aggregate**: "metric aggregate", "how many placed orders last month", "sum the order value by day".
- **Campaign performance report**: "campaign performance report", "open rate / click rate for campaigns", "revenue report by campaign".
- **Flow performance report**: "flow performance report", "how are my flows performing", "flow revenue by week".

## When NOT to use

- **Metric definitions / custom metrics** — these scripts only read existing
  metrics and query aggregates/reports; they do not create or edit metric
  definitions. Use the Klaviyo API or UI.
- **Ad-hoc analytics not covered by the report shapes** — the report scripts
  build `campaign-values-report` / `flow-values-report` bodies with a preset
  timeframe and statistics list. For other report types or richer query shapes,
  use the Klaviyo REST API directly.
- **Flows, campaigns, events, templates, profiles, segments** — use the matching
  skill (`klaviyo-flows`, `klaviyo-campaigns`, `klaviyo-templates`,
  `klaviyo-profiles`, `klaviyo-lists`) or the Klaviyo MCP server / REST API.

## Prerequisites

- `KLAVIYO_PRIVATE_API_KEY` is set in the environment (read at client
  construction). If a script returns an auth-shaped error, stop and confirm the key.
- The dated API `revision` header comes from `domains.klaviyo.api_version` in
  `store-config.yaml`, falling back to the client default; override per call with
  `--revision`.
- Install deps: `uv sync --extra klaviyo`.

Common flags from `klaviyo.utils.cli`: `--output table|json|markdown`, `--limit`,
`--config`, `--verbose`, `--revision`, and `--dry-run` on the POST queries.

## Metric scripts

### List metrics (read-only)

```bash
uv run klaviyo/scripts/metrics/list.py
```

Flattens each metric to `id`, `name`, `integration`, `created`, `updated`.
Honors `--limit` via cursor pagination. Use this to find the metric id you need
for `aggregate` or for a report's `--conversion-metric-id`.

### Show one metric (read-only)

```bash
uv run klaviyo/scripts/metrics/get.py --id ABC123
```

`--id` is required.

### Metric aggregate (read-style POST, dry-run to preview)

```bash
# Preview the JSON:API body without calling the API:
uv run klaviyo/scripts/metrics/aggregate.py \
  --metric-id ABC123 --measurement count --measurement sum_value \
  --interval day --start 2026-01-01T00:00:00Z --end 2026-02-01T00:00:00Z --dry-run

# Run the query:
uv run klaviyo/scripts/metrics/aggregate.py \
  --metric-id ABC123 --measurement count \
  --start 2026-01-01T00:00:00Z --end 2026-02-01T00:00:00Z
```

Required: `--metric-id`, at least one `--measurement` (repeatable: `count`,
`sum_value`, `unique`, ...), `--start` and `--end` (ISO-8601; start inclusive,
end exclusive). Optional: `--interval` (`hour`|`day`|`week`|`month`, default
`day`), `--timezone` (IANA, e.g. `UTC`). This is a POST that only queries data —
it mutates nothing — but `--dry-run` still prints the request body and skips the
POST. Not `--yes`-gated.

## Report scripts

Both reports are read-style POST queries. They mutate nothing, honor `--dry-run`
to preview the JSON:API body, and are **not** `--yes`-gated. Both **require
`--conversion-metric-id`** — the metric Klaviyo attributes conversions to
(typically the Placed Order metric; find its id with `metrics/list.py`).

### Campaign performance report

```bash
# Preview the body:
uv run klaviyo/scripts/reports/campaign.py \
  --statistic opens --statistic clicks --statistic conversion_value \
  --conversion-metric-id ABC123 --timeframe last_30_days --dry-run

# Run it:
uv run klaviyo/scripts/reports/campaign.py \
  --statistic opens --statistic clicks \
  --conversion-metric-id ABC123 --timeframe last_30_days
```

Required: at least one `--statistic` (repeatable: `opens`, `clicks`, `revenue`,
...) and `--conversion-metric-id`. Optional: `--timeframe` (preset key, default
`last_30_days`; e.g. `last_12_months`), `--filter` (a JSON:API filter expression
to scope the report).

### Flow performance report

```bash
# Preview the body:
uv run klaviyo/scripts/reports/flow.py \
  --statistic opens --statistic clicks --statistic conversion_value \
  --conversion-metric-id ABC123 --timeframe last_30_days --interval weekly --dry-run

# Run it:
uv run klaviyo/scripts/reports/flow.py \
  --statistic opens --statistic clicks \
  --conversion-metric-id ABC123 --interval daily
```

Same shape as the campaign report, plus `--interval`
(`daily`|`weekly`|`monthly`, default `daily`). Required: at least one
`--statistic` and `--conversion-metric-id`.

## Reference

For metric definitions, report types beyond the campaign/flow value reports, and
anything not exposed by these scripts, use the Klaviyo MCP server or the Klaviyo
REST API directly.
