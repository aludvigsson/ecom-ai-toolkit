---
name: klaviyo-templates
description: Manage Klaviyo email templates via the templates/ CLI scripts. Use when the user says list templates, show a template, create a template, update a template, delete a template, render a template, clone a template, or assign a template to a campaign. list/get/render are read-only-ish reads; create, update, render, clone, and assign honor --dry-run; only delete additionally requires --yes for live execution. Template HTML is supplied via --html (inline) or --html-file (path); render/assign context is supplied as JSON. Drag-and-drop / DnD template editing is not supported here — defer to direct Klaviyo API use.
---

# klaviyo-templates

## When to use

- **List templates**: "list templates", "show my email templates".
- **Show a template**: "show template abc123", "get that template's HTML".
- **Create a template**: "create a template", "make a new email template from this HTML".
- **Update a template**: "update template abc123", "change the template's HTML".
- **Delete a template**: "delete template abc123", "remove that template".
- **Render a template**: "render template abc123 with this context", "preview the merged HTML".
- **Clone a template**: "clone template abc123", "duplicate that template".
- **Assign a template to a campaign**: "assign template abc123 to that campaign message", "wire this template onto the campaign".

## When NOT to use

- **Drag-and-drop (DnD) template editing** — these scripts manage HTML templates;
  Klaviyo's structured DnD editor blocks are not exposed. Use the Klaviyo API
  directly for DnD template authoring.
- **Creating / scheduling / sending the campaign itself** — use the
  `klaviyo-campaigns` skill (`assign` here only links a template to an existing
  campaign message).
- Anything not exposed by these scripts — use the Klaviyo MCP server or REST API.

## Prerequisites

- `KLAVIYO_PRIVATE_API_KEY` is set in the environment (read at client
  construction). If a script returns an auth-shaped error, stop and confirm the key.
- The dated API `revision` header comes from `domains.klaviyo.api_version` in
  `store-config.yaml`, falling back to the client default; override per call with
  `--revision`.
- Install deps: `uv sync --extra klaviyo`.

Common flags from `klaviyo.utils.cli`: `--output table|json|markdown`, `--limit`,
`--config`, `--verbose`, `--revision`, and on mutations `--dry-run` / `--yes`.

## Template scripts

### List templates (read-only)

```bash
uv run klaviyo/scripts/templates/list.py
```

### Show one template (read-only)

```bash
uv run klaviyo/scripts/templates/get.py --id 01HXXXX
```

`--id` is required.

### Create a template (dry-run first)

```bash
uv run klaviyo/scripts/templates/create.py --name "Welcome" --html-file welcome.html --dry-run
uv run klaviyo/scripts/templates/create.py --name "Welcome" --html "<h1>Hi</h1>"
```

`--name` is required. HTML comes from `--html` (inline) or `--html-file` (path);
optional `--text` sets a plain-text body. `--dry-run` prints the JSON:API body and
skips the POST.

### Update a template (dry-run first)

```bash
uv run klaviyo/scripts/templates/update.py --id 01HXXXX --html-file welcome.html --dry-run
uv run klaviyo/scripts/templates/update.py --id 01HXXXX --name "Welcome v2"
```

`--id` is required. Settable: `--name`, `--html` / `--html-file`, `--text`.
`--dry-run` prints the body and skips the PATCH.

### Render a template (dry-run first)

```bash
uv run klaviyo/scripts/templates/render.py --id 01HXXXX --context '{"first_name":"Jane"}' --dry-run
uv run klaviyo/scripts/templates/render.py --id 01HXXXX --context-file ctx.json
```

`--id` is required. Render context comes from `--context` (inline JSON string) or
`--context-file` (path to a JSON file). `--dry-run` prints the request body and
skips the POST.

### Clone a template (dry-run first)

```bash
uv run klaviyo/scripts/templates/clone.py --id 01HXXXX --name "Welcome (copy)" --dry-run
uv run klaviyo/scripts/templates/clone.py --id 01HXXXX --name "Welcome (copy)"
```

`--id` (source template) and `--name` (clone's name) are required. `--dry-run`
prints the request body and skips the POST.

### Assign a template to a campaign message (dry-run first)

```bash
uv run klaviyo/scripts/templates/assign.py --message-id MSG123 --template-id 01HXXXX --dry-run
uv run klaviyo/scripts/templates/assign.py --message-id MSG123 --template-id 01HXXXX
```

`--message-id` (the campaign message id) and `--template-id` are required.
`--dry-run` prints the request body and skips the call. The message id comes from a
campaign's `campaign-messages` — see the `klaviyo-campaigns` skill.

### Delete a template (dry-run, then `--yes`)

```bash
uv run klaviyo/scripts/templates/delete.py --id 01HXXXX --dry-run

# Confirm with --yes:
uv run klaviyo/scripts/templates/delete.py --id 01HXXXX --yes
```

Destructive — the only template op gated by `--yes`. `--dry-run` prints the
intended deletion and exits 0 without `--yes`; live execution requires `--yes`.

## Reference

For drag-and-drop (DnD) template authoring, template versioning, and anything not
exposed by these scripts, use the Klaviyo MCP server or the Klaviyo REST API
directly.
