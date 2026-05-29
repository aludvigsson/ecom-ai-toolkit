---
name: klaviyo-flows
description: Manage Klaviyo flows and their adjacent event activity via the flows/ and events/ CLI scripts. Use when the user says list Klaviyo flows, show flow details, show flow actions, activate a flow, deactivate a flow, turn a flow live, set a flow to draft or manual, list events, or track an event. flows/list, flows/get, and events/list are read-only and honor --output table|json|markdown; flows/update_status and events/create honor --dry-run; flows/update_status (which can take a flow live) additionally requires --yes for live execution. Flow definition / authoring (adding actions, editing branches, building triggers) is not supported here — defer to direct Klaviyo API or UI use.
---

# klaviyo-flows

## When to use

- **List flows**: "list Klaviyo flows", "show my flows", "what flows do I have".
- **Show flow details**: "show flow abc123", "get the details of that flow".
- **Show flow actions**: "show flow actions", "what steps are in that flow".
- **Activate a flow**: "activate that flow", "turn the flow live", "set the flow to live".
- **Deactivate a flow**: "deactivate that flow", "set the flow to draft", "pause the flow".
- **List events**: "list events", "show recent events for that metric/profile".
- **Track an event**: "track an event", "record a custom event for this customer".

Events are folded in here as flow-adjacent activity — flows are triggered by
metrics/events, so listing and recording events lives alongside the flow scripts.

## When NOT to use

- **Flow definition / authoring** — adding actions, editing branches, building or
  changing triggers, or otherwise composing a flow's structure is not exposed.
  These scripts only read flows and toggle a flow's status. Use the Klaviyo API or
  the Klaviyo UI to author flows.
- **Metrics, reports, campaigns, templates, profiles, segments** — use the matching
  skill (`klaviyo-metrics`, `klaviyo-campaigns`, `klaviyo-templates`,
  `klaviyo-profiles`, `klaviyo-lists`) or the Klaviyo MCP server / REST API.

## Prerequisites

- `KLAVIYO_PRIVATE_API_KEY` is set in the environment (read at client
  construction). If a script returns an auth-shaped error, stop and confirm the key.
- The dated API `revision` header comes from `domains.klaviyo.api_version` in
  `store-config.yaml`, falling back to the client default; override per call with
  `--revision`.
- Install deps: `uv sync --extra klaviyo`.

Common flags from `klaviyo.utils.cli`: `--output table|json|markdown`, `--limit`,
`--config`, `--verbose`, `--revision`, and on mutations `--dry-run` / `--yes`.

## Flow scripts

### List flows (read-only)

```bash
uv run klaviyo/scripts/flows/list.py
uv run klaviyo/scripts/flows/list.py --status live   # filter by status (e.g. live, draft, manual)
```

`--status` filters the returned flows.

### Show one flow (read-only)

```bash
uv run klaviyo/scripts/flows/get.py --id 01HXXXX
uv run klaviyo/scripts/flows/get.py --id 01HXXXX --with-actions   # also include the flow's actions
```

`--id` is required. `--with-actions` additionally paginates the flow's
`flow-actions` and includes them in the output.

### Activate / deactivate a flow (dry-run, then `--yes`)

```bash
# Dry-run a status change (prints the JSON:API body, no API call):
uv run klaviyo/scripts/flows/update_status.py --id 01HXXXX --status live --dry-run

# Confirm with --yes (this can take a flow LIVE — it will start sending):
uv run klaviyo/scripts/flows/update_status.py --id 01HXXXX --status live --yes

# Set back to draft / manual:
uv run klaviyo/scripts/flows/update_status.py --id 01HXXXX --status draft --yes
```

**High-stakes — `--status live` makes the flow start sending.** `--id` and
`--status` (one of `live`, `manual`, `draft`) are required. `--dry-run` works
without `--yes` and prints the request body without calling the API; live
execution requires `--yes`.

## Event scripts

### List events (read-only)

```bash
uv run klaviyo/scripts/events/list.py
uv run klaviyo/scripts/events/list.py --metric-id METRIC123    # filter by metric
uv run klaviyo/scripts/events/list.py --profile-id PROF123     # filter by profile
uv run klaviyo/scripts/events/list.py --since 2026-01-01T00:00:00Z   # lower bound on event datetime
```

All filters are optional and may be combined.

### Track an event (dry-run first)

```bash
uv run klaviyo/scripts/events/create.py \
  --metric-name "Placed Order" --email jane@example.com \
  --value 49.99 --properties '{"order_id":"1001"}' --dry-run

# Looks right? Drop --dry-run:
uv run klaviyo/scripts/events/create.py \
  --metric-name "Placed Order" --email jane@example.com --value 49.99
```

`--metric-name` is required, plus at least one of `--email` or `--phone-number`
to identify the profile. Optional: `--properties` (JSON object string, default
`{}`), `--value` (numeric event value), `--time` (ISO-8601; defaults to now
server-side). `--dry-run` prints the JSON:API body and skips the POST. `create`
is not `--yes`-gated.

## Reference

For flow authoring (adding actions, editing branches, building triggers), flow
messages/templates, and anything not exposed by these scripts, use the Klaviyo
MCP server or the Klaviyo REST API directly.
