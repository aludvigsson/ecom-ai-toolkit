---
name: klaviyo-campaigns
description: Manage Klaviyo email campaigns via the campaigns/ CLI scripts. Use when the user says list campaigns, show a campaign, create a campaign, schedule a campaign, send a campaign now, cancel a scheduled send, or delete a campaign. list/get are read-only and honor --output table|json|markdown; create, schedule, and cancel honor --dry-run; schedule (the highest-stakes op — it triggers the actual send), cancel, and delete additionally require --yes for live execution. Multi-message / multi-channel campaigns and flow authoring are not supported here — defer to direct Klaviyo API use.
---

# klaviyo-campaigns

## When to use

- **List campaigns**: "list campaigns", "show my email campaigns", "what campaigns do I have".
- **Show a campaign**: "show campaign abc123", "get the details of that campaign".
- **Create a campaign**: "create a campaign", "draft a new email campaign to list X".
- **Schedule a campaign**: "schedule that campaign for tomorrow 9am", "send the campaign now".
- **Cancel a scheduled send**: "cancel the scheduled send", "stop that campaign from going out".
- **Delete a campaign**: "delete campaign abc123", "remove that draft campaign".

## When NOT to use

- **Multi-message or multi-channel campaigns** (A/B variants, SMS + email in one
  campaign, several messages per campaign) — `create.py` builds a single
  single-channel message. Use the Klaviyo API directly for richer campaign shapes.
- **Templates / message bodies** — to author the HTML a campaign sends, or to wire
  a template onto a campaign message, use the `klaviyo-templates` skill.
- **Flows, metrics, events, profiles, segments** — use the matching skill
  (`klaviyo-profiles`, `klaviyo-lists`) or the Klaviyo MCP server / REST API.

## Prerequisites

- `KLAVIYO_PRIVATE_API_KEY` is set in the environment (read at client
  construction). If a script returns an auth-shaped error, stop and confirm the key.
- The dated API `revision` header comes from `domains.klaviyo.api_version` in
  `store-config.yaml`, falling back to the client default; override per call with
  `--revision`.
- Install deps: `uv sync --extra klaviyo`.

Common flags from `klaviyo.utils.cli`: `--output table|json|markdown`, `--limit`,
`--config`, `--verbose`, `--revision`, and on mutations `--dry-run` / `--yes`.

## Campaign scripts

### List campaigns (read-only)

```bash
uv run klaviyo/scripts/campaigns/list.py
uv run klaviyo/scripts/campaigns/list.py --channel email   # channel filter (Klaviyo requires one; default email)
```

Klaviyo requires a channel filter on the campaigns endpoint, so `--channel`
defaults to `email`.

### Show one campaign (read-only)

```bash
uv run klaviyo/scripts/campaigns/get.py --id 01HXXXX
```

`--id` is required.

### Create a campaign (dry-run first)

```bash
uv run klaviyo/scripts/campaigns/create.py \
  --name "Spring Sale" --subject "20% off everything" \
  --from-email hello@example.com --from-label "Acme" \
  --list-id ABC123 --dry-run

# Looks right? Drop --dry-run:
uv run klaviyo/scripts/campaigns/create.py \
  --name "Spring Sale" --subject "20% off everything" \
  --from-email hello@example.com --from-label "Acme" \
  --list-id ABC123
```

Required: `--name`, `--subject`, `--from-email`, `--from-label`. Audience:
`--list-id` and/or `--segment-id` (added to `included`), `--exclude-id` (added to
`excluded`). Other: `--preview-text`, `--channel` (default `email`). `--dry-run`
prints the JSON:API body and skips the POST. Creating a campaign leaves it in
draft — it does not send anything until you `schedule` it.

### Schedule or send a campaign (dry-run, then `--yes`)

```bash
# Dry-run a future send:
uv run klaviyo/scripts/campaigns/schedule.py --id 01HXXXX --at 2026-06-01T09:00:00 --dry-run

# Confirm a scheduled send with --yes:
uv run klaviyo/scripts/campaigns/schedule.py --id 01HXXXX --at 2026-06-01T09:00:00 --yes

# Send immediately (still requires --yes):
uv run klaviyo/scripts/campaigns/schedule.py --id 01HXXXX --send-now --yes
```

**Highest-stakes operation in the domain — this is what actually sends mail.**
`--id` is required, plus exactly one of `--at` (ISO-8601 send time) or
`--send-now`. `--dry-run` works without `--yes` and prints the request body
without calling the API; live execution requires `--yes`.

### Cancel a scheduled send (dry-run, then `--yes`)

```bash
uv run klaviyo/scripts/campaigns/cancel.py --id 01HXXXX --dry-run

# Confirm with --yes:
uv run klaviyo/scripts/campaigns/cancel.py --id 01HXXXX --yes
```

High-stakes. `--id` is required. `--dry-run` works without `--yes` and prints the
request body; live execution requires `--yes`.

### Delete a campaign (dry-run, then `--yes`)

```bash
uv run klaviyo/scripts/campaigns/delete.py --id 01HXXXX --dry-run

# Confirm with --yes:
uv run klaviyo/scripts/campaigns/delete.py --id 01HXXXX --yes
```

Destructive. `--dry-run` prints the intended deletion and exits 0 without `--yes`;
live execution requires `--yes`.

## Note on the send / cancel endpoint

The send-job (`schedule`/`send-now`) and `cancel` endpoints are revision-sensitive.
Their request shapes were verified against the toolkit default revision in
`docs/superpowers/notes/klaviyo-send-endpoint.md` (stable across recent dated
revisions). If a future revision changes them, update per that note.

## Reference

For multi-message / A/B / multi-channel campaigns, flows, metrics, events, and
anything not exposed by these scripts, use the Klaviyo MCP server or the Klaviyo
REST API directly.
