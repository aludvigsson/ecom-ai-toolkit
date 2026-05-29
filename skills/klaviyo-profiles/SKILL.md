---
name: klaviyo-profiles
description: Manage Klaviyo profiles and read segments via the profiles/ and segments/ CLI scripts. Use when the user says list profiles, find profile by email, create a profile, update a profile, subscribe a profile, unsubscribe a profile, list segments, or show segment members. list/get/segments are read-only and honor --output table|json|markdown; create, update, subscribe, and unsubscribe honor --dry-run; unsubscribe additionally requires --yes for live execution. Segment authoring (creating/editing segment definitions) is not supported here — defer to direct Klaviyo API use.
---

# klaviyo-profiles

## When to use

- **List profiles**: "list profiles", "show profiles in list X", "who's in segment Y", filter by exact email / list membership / segment membership.
- **Find a profile**: "find the profile for jane@example.com", "get profile id abc123".
- **Create a profile**: "create a profile for jane@example.com", "add a new contact".
- **Update a profile**: "update jane's name", "change the phone number on profile abc123".
- **Subscribe a profile**: "subscribe jane to list X", "opt this email into marketing".
- **Unsubscribe a profile**: "unsubscribe jane from list X", "opt this email out".
- **Read segments**: "list segments", "show segment members", "what's in segment Y".

## When NOT to use

- **Segment authoring** — creating, editing, or defining segment conditions is **not** exposed. `segments/list.py` and `segments/get.py` are read-only (spec §2 / §10). Use the Klaviyo API directly for segment definitions.
- **List CRUD** (create/rename/delete lists, bulk add/remove membership) — use the `klaviyo-lists` skill.
- Anything not exposed by these scripts (events, metrics, flows, campaigns, catalog) — use the Klaviyo MCP server or the API directly.

## Prerequisites

- `KLAVIYO_PRIVATE_API_KEY` is set in the environment (read at client construction). If a script returns an auth-shaped error, stop and confirm the key.
- The dated API `revision` header comes from `domains.klaviyo.api_version` in `store-config.yaml`, falling back to the client default; override per call with `--revision`.
- Install deps: `uv sync --extra klaviyo`.

Common flags from `klaviyo.utils.cli`: `--output table|json|markdown`, `--limit`, `--config`, `--verbose`, `--revision`, and on mutations `--dry-run` / `--yes`.

## Profile scripts

### List profiles

```bash
uv run klaviyo/scripts/profiles/list.py
uv run klaviyo/scripts/profiles/list.py --email jane@example.com   # exact match
uv run klaviyo/scripts/profiles/list.py --list-id ABC123          # list membership
uv run klaviyo/scripts/profiles/list.py --segment-id SEG123       # segment membership
```

### Get one profile

```bash
uv run klaviyo/scripts/profiles/get.py --id 01HXXXX
uv run klaviyo/scripts/profiles/get.py --email jane@example.com   # resolved to id
```

One of `--id` or `--email` is required.

### Create a profile (dry-run first)

```bash
uv run klaviyo/scripts/profiles/create.py --email jane@example.com --first-name Jane --dry-run
uv run klaviyo/scripts/profiles/create.py --email jane@example.com --first-name Jane
```

At least one of `--email` or `--phone-number` is required. Other attributes:
`--first-name`, `--last-name`, `--phone-number` (E.164). `--dry-run` prints the
JSON:API body and skips the POST.

### Update a profile (dry-run first)

```bash
uv run klaviyo/scripts/profiles/update.py --id 01HXXXX --first-name Jane --dry-run
uv run klaviyo/scripts/profiles/update.py --id 01HXXXX --first-name Jane
```

`--id` is required; the id is carried inside the JSON:API `data` body. Settable
attributes: `--email`, `--phone-number`, `--first-name`, `--last-name`.
`--dry-run` prints the body and skips the PATCH.

### Subscribe a profile (dry-run first)

```bash
uv run klaviyo/scripts/profiles/subscribe.py --list-id ABC123 --email jane@example.com --dry-run
uv run klaviyo/scripts/profiles/subscribe.py --list-id ABC123 --email jane@example.com
```

Builds a profile-subscription-bulk-create-job for a single profile. `--list-id`
is required; at least one of `--email` or `--phone-number` is required.
`--dry-run` prints the body and skips the API call.

### Unsubscribe a profile (dry-run, then `--yes`)

```bash
uv run klaviyo/scripts/profiles/unsubscribe.py --list-id ABC123 --email jane@example.com --dry-run

# Confirm with --yes:
uv run klaviyo/scripts/profiles/unsubscribe.py --list-id ABC123 --email jane@example.com --yes
```

High-stakes. `--dry-run` works without `--yes` and prints the body without
calling the API; live execution requires `--yes`. `--list-id` is required; at
least one of `--email` or `--phone-number` is required.

## Segment scripts (read-only)

### List segments

```bash
uv run klaviyo/scripts/segments/list.py
```

### Get a segment, optionally with members

```bash
uv run klaviyo/scripts/segments/get.py --id SEG123
uv run klaviyo/scripts/segments/get.py --id SEG123 --with-members   # capped by --limit
```

`--with-members` appends a paginated profile listing under a `members` key
(capped by `--limit`). Read-only.

## Reference

For segment authoring (creating/editing segment definitions), events, metrics,
flows, and anything not covered by these scripts, use the Klaviyo MCP server or
the Klaviyo REST API directly.
