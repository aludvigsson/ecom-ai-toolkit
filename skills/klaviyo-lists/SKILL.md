---
name: klaviyo-lists
description: Manage Klaviyo lists via the lists/ CLI scripts — list my Klaviyo lists, get a list, create a list, rename a list, delete a list, add profiles to a list, remove profiles from a list. Use when the user says list my Klaviyo lists, create a list, rename a list, delete a list, add profiles to a list, or remove profiles from a list. list/get are read-only and honor --output table|json|markdown; create, update, delete, add_profiles, and remove_profiles honor --dry-run; the destructive delete and remove_profiles additionally require --yes for live execution.
---

# klaviyo-lists

## When to use

- **List your lists**: "list my Klaviyo lists", "what lists do I have".
- **Get a list**: "show list ABC123", "who's on list ABC123" (with members).
- **Create a list**: "create a list called VIP".
- **Rename a list**: "rename list ABC123 to VIP".
- **Delete a list**: "delete list ABC123".
- **Add profiles to a list**: "add these profile ids to list ABC123".
- **Remove profiles from a list**: "remove these profile ids from list ABC123".

## When NOT to use

- **Profile CRUD, subscribe/unsubscribe (marketing consent), segments** — use the
  `klaviyo-profiles` skill. `add_profiles`/`remove_profiles` here change list
  *membership* via relationships; they do **not** change marketing consent.
- Anything not exposed by these scripts (flows, campaigns, metrics, events) — use
  the Klaviyo MCP server or the API directly.

## Prerequisites

- `KLAVIYO_PRIVATE_API_KEY` is set in the environment. If a script returns an
  auth-shaped error, stop and confirm the key.
- The dated API `revision` header comes from `domains.klaviyo.api_version` in
  `store-config.yaml`, falling back to the client default; override with
  `--revision`.
- Install deps: `uv sync --extra klaviyo`.

Common flags from `klaviyo.utils.cli`: `--output table|json|markdown`, `--limit`,
`--config`, `--verbose`, `--revision`, and on mutations `--dry-run` / `--yes`.

## List scripts

### List lists

```bash
uv run klaviyo/scripts/lists/list.py
```

### Get a list, optionally with members

```bash
uv run klaviyo/scripts/lists/get.py --id ABC123
uv run klaviyo/scripts/lists/get.py --id ABC123 --with-members   # capped by --limit
```

`--id` is required. `--with-members` appends a paginated profile listing under a
`members` key (capped by `--limit`).

### Create a list (dry-run first)

```bash
uv run klaviyo/scripts/lists/create.py --name "VIP" --dry-run
uv run klaviyo/scripts/lists/create.py --name "VIP"
```

`--name` is required. `--dry-run` prints the body and skips the POST.

### Rename a list (dry-run first)

```bash
uv run klaviyo/scripts/lists/update.py --id ABC123 --name "VIP 2026" --dry-run
uv run klaviyo/scripts/lists/update.py --id ABC123 --name "VIP 2026"
```

`--id` and `--name` are required. `--dry-run` prints the body and skips the PATCH.

### Delete a list (dry-run, then `--yes`)

```bash
uv run klaviyo/scripts/lists/delete.py --id ABC123 --dry-run

# Confirm with --yes:
uv run klaviyo/scripts/lists/delete.py --id ABC123 --yes
```

Destructive. `--dry-run` prints the intended deletion and exits 0 without
`--yes`; live execution requires `--yes`.

### Add profiles to a list (dry-run first)

```bash
uv run klaviyo/scripts/lists/add_profiles.py --id ABC123 \
  --profile-id 01HAAA --profile-id 01HBBB --dry-run
uv run klaviyo/scripts/lists/add_profiles.py --id ABC123 \
  --profile-id 01HAAA --profile-id 01HBBB
```

`--id` is required; pass one or more `--profile-id` values. Builds a JSON:API
relationship body. `--dry-run` prints the body and skips the POST.

### Remove profiles from a list (dry-run, then `--yes`)

```bash
uv run klaviyo/scripts/lists/remove_profiles.py --id ABC123 \
  --profile-id 01HAAA --profile-id 01HBBB --dry-run

# Confirm with --yes:
uv run klaviyo/scripts/lists/remove_profiles.py --id ABC123 \
  --profile-id 01HAAA --profile-id 01HBBB --yes
```

High-stakes. `--dry-run` works without `--yes` and prints the body without
calling the API; live execution requires `--yes`. `--id` is required; pass one
or more `--profile-id` values.

## Reference

For flows, campaigns, metrics, events, and anything not covered by these scripts,
use the Klaviyo MCP server or the Klaviyo REST API directly.
