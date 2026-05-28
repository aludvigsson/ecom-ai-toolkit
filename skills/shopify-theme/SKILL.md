---
name: shopify-theme
description: List, read, and update Online Store 2.0 theme files via the theme/ CLI scripts. Use when the user says list themes, read theme file, templates/product.json, sections/header.liquid, edit theme file, deploy theme change, diff theme file before deploy, or what's in my live theme. Hydrogen storefronts are OUT of scope — edits go in your Hydrogen repo. --dry-run is mandatory before write; --yes required for live execution.
---

# shopify-theme

## When to use

- User wants to **list themes** in the store: "what themes do I have?", "show me my live theme ID", "list unpublished themes", "what's the dev theme called?".
- User wants to **read a single theme file**: "show me `templates/product.json`", "what's in `sections/header.liquid`?", "dump the snippet for the cart drawer", "what's in my live theme?".
- User wants to **update a single theme file**: "edit `sections/header.liquid` to add X", "deploy this template change", "diff this new file against the live theme before pushing", "patch the version snippet".

## When NOT to use

- **Hydrogen storefronts** — `update_asset.py` is OS 2.0 only. For Hydrogen, edits happen in your separate React/Remix repo, not in Shopify. Delegate to your local Hydrogen repo.
- **Bulk theme migration / multi-file deploys** — not supported in v0.4 (single-file updates only). Use Shopify CLI's `shopify theme push` for whole-theme deploys.
- **Theme creation / duplication** — Shopify CLI's `shopify theme push` and the Admin UI handle that.
- **Binary asset uploads** (images, fonts) — `get_asset.py` / `update_asset.py` only handle text bodies. Use the Admin UI or `shopify theme push` for binary assets.
- Auth not working / "is my shop connected?" — delegate to `shopify-auth`.
- Anything not exposed by `list.py` / `get_asset.py` / `update_asset.py` (theme publishing, deleting, duplicating, settings_data.json bulk merges) — use `shopify-plugin:shopify-admin` directly.

## Prerequisites

- `shopify-auth` or `setup.py` has run successfully **OR** `store-config.yaml` and `.env.local` exist at repo root with `SHOPIFY_ADMIN_ACCESS_TOKEN` populated.
- The token must have `read_themes` scope (for `list.py` / `get_asset.py`) **and** `write_themes` scope (for `update_asset.py`). If your token was created without write scope, re-auth: custom-app users regenerate the token with the wider scopes; CLI users re-run `shopify store auth`.
- Project deps installed: `uv sync --extra shopify`.

If any script in this skill returns an auth-shaped error, stop and delegate to `shopify-auth`.

## How the scripts split

- **`list.py` shows all themes** with their role (`MAIN`, `UNPUBLISHED`, `DEMO`, `DEVELOPMENT`). Use this to find the theme ID you want to read or edit.
- **`get_asset.py` reads a single file** from a theme — prints content to stdout (text mode default) so you can pipe into your editor or diff.
- **`update_asset.py` writes a single file:** fetches the current content, prints a unified diff to stderr, then upserts only if `--yes` is passed. `--dry-run` always skips the write.

## Canonical workflows

### 1. List all themes

```bash
uv run shopify/scripts/theme/list.py
```

### 2. List only unpublished themes (e.g. to find a safe edit target)

```bash
uv run shopify/scripts/theme/list.py --role UNPUBLISHED
```

### 3. Read a template

```bash
uv run shopify/scripts/theme/get_asset.py \
  --theme-id gid://shopify/OnlineStoreTheme/12345 \
  --filename templates/product.json
```

### 4. Read a section as JSON (for piping into jq)

```bash
uv run shopify/scripts/theme/get_asset.py \
  --theme-id gid://shopify/OnlineStoreTheme/12345 \
  --filename sections/header.liquid \
  --output json | jq -r '.body.content'
```

### 5. Dry-run an update (ALWAYS do this first)

```bash
uv run shopify/scripts/theme/update_asset.py \
  --theme-id gid://shopify/OnlineStoreTheme/12345 \
  --filename sections/header.liquid \
  --from-file new-header.liquid \
  --dry-run
```

Reads the local file, fetches the current theme content, prints a unified diff to stderr. No write.

### 6. Apply the update (after reviewing the dry-run diff)

```bash
uv run shopify/scripts/theme/update_asset.py \
  --theme-id gid://shopify/OnlineStoreTheme/12345 \
  --filename sections/header.liquid \
  --from-file new-header.liquid \
  --yes
```

### 7. Update from stdin (for piped content)

```bash
cat new-header.liquid | uv run shopify/scripts/theme/update_asset.py \
  --theme-id gid://shopify/OnlineStoreTheme/12345 \
  --filename sections/header.liquid \
  --content-stdin \
  --yes
```

### 8. Inline update for tiny changes

```bash
uv run shopify/scripts/theme/update_asset.py \
  --theme-id gid://shopify/OnlineStoreTheme/12345 \
  --filename snippets/version.liquid \
  --content "{% assign v = 'v2.3.1' %}" \
  --yes
```

## Common pitfalls

- **`update_asset.py` is OS 2.0 only.** Hydrogen storefronts have no `themes` connection — the script will error if you try. Hydrogen edits happen in your Remix repo, not via the Admin API.
- **`--yes` is required for live execution.** Without it the script refuses to write. `--dry-run` short-circuits everything before any check — use it to confirm the resolved theme ID, filename, and diff before applying.
- **The diff is printed to stderr, not stdout.** This keeps stdout clean for piping. Redirect `2>diff.patch` if you want to capture it for a code review.
- **`get_asset.py` exits with code 2 if the file is not found** in the theme. Use this to detect missing files in scripts (e.g. `if ! get_asset.py ...; then echo "missing"; fi`).
- **Updating a JSON template** (`templates/product.json`, `templates/index.json`, `templates/*.json`) requires valid JSON. The script does NOT validate JSON before sending — Shopify will reject malformed JSON via `userErrors`. Recommend a `python -m json.tool < new-template.json > /dev/null` check before applying.
- **Updating a Liquid file** (`sections/*.liquid`, `snippets/*.liquid`, `templates/*.liquid`) does not validate Liquid syntax. A broken file will brick the live storefront if applied to the MAIN theme. **Always preview on an UNPUBLISHED duplicate first** — duplicate the live theme in the Admin UI, push your change there, preview, then promote.
- **Binary asset bodies are not supported.** Theme assets with bodies stored as `OnlineStoreThemeFileBodyUrl` (images, fonts, other binaries) return a URL, not text. `get_asset.py` only handles text bodies. For binary assets use the Shopify Admin UI or `shopify theme pull`.
- **Scope requirements:** the token needs `read_themes` for `list` / `get_asset` and `write_themes` for `update_asset`. If your token was created without write scope, re-auth (custom-app: regenerate token with `write_themes`; CLI: re-run `shopify store auth` with the wider scopes).

## Reference

For Liquid syntax and theme directory structure, defer to the `shopify-plugin:shopify-liquid` skill. For the full `OnlineStoreTheme`, `OnlineStoreThemeFileBodyText`, `OnlineStoreThemeFileBodyUrl`, and `themeFilesUpsert` schemas (plus `themePublish`, `themeDelete`, `themeDuplicate`, and the `OnlineStoreThemeRole` enum), defer to the `shopify-plugin:shopify-admin` skill from the Shopify-AI-Toolkit plugin dependency.
