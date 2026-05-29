# Plan K1: Klaviyo Foundation + Audience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Klaviyo domain foundation (`KlaviyoClient`, CLI helpers, packaging/config wiring) plus the full audience cluster of CLI scripts — profiles, lists, and segments — so a Klaviyo account's audience can be managed end-to-end from `uv run klaviyo/scripts/<cluster>/<op>.py`.

**Architecture:** A new `klaviyo/utils/client.py` puts a thin `KlaviyoClient` over `core.http.HttpClient` (JSON:API over httpx; Klaviyo-API-Key auth; dated `revision` header from `domains.klaviyo.api_version`; cursor pagination via `links.next`; `check_errors` raising `KlaviyoAPIError`). `klaviyo/utils/cli.py` near-copies `shopify/utils/cli.py` and adds `add_klaviyo_flags` for `--revision`/`--yes`. Audience scripts mirror the Shopify webhooks scripts: one script per operation, `--dry-run` on every mutation, `--yes` gating the high-stakes set, JSON:API resources flattened into flat rows for table output.

**Tech Stack:** `httpx>=0.27`, `pyyaml>=6`, `pydantic>=2.7` (the existing `shopify` base deps, now populated for the `klaviyo` extra). Tests use `pytest` with `monkeypatch`/`unittest.mock.patch`. No vendor SDK, no MCP.

**Spec reference:** `docs/superpowers/specs/2026-05-29-klaviyo-domain-design.md` §3 (architecture — `client.py` §3.1, `cli.py` §3.2), §4 (conventions), §5 K1 (audience script inventory), §9 (config & secrets), §11 (implementation split — Plan K1), §12 (definition of done, scoped to K1).

**Depends on:** v1 foundation (`core/http.py`, `core/config.py` `DomainConfig.api_version`, `core/secrets.require_secret`). The reserved `klaviyo` extra and `KLAVIYO_PRIVATE_API_KEY` env entry already exist. No `core/` changes. The Shopify domain (`shopify/utils/{client,cli}.py`, `shopify/scripts/webhooks/*`) is the reference implementation copied here.

> **Scope note — `--all` deferred:** Spec §4 mentions an `--all` flag (opt-out of the `--limit` cap). K1 intentionally ships only `--limit`-capped pagination; `KlaviyoClient.paginate(limit=None)` supports unbounded iteration internally, but **no `--all` CLI flag is registered in any K-plan**. Do not add `--all` to match the spec text — it is a tracked domain-wide follow-up, not part of this plan's Definition of Done.

---

## File Structure

| Path | Responsibility |
|---|---|
| `pyproject.toml` | Populate `klaviyo` extra with base deps (modify) |
| `store-config.example.yaml` | `domains.klaviyo` → `{enabled, api_version}` (modify) |
| `.github/workflows/ci.yml` | Add `--extra klaviyo` to sync step (modify) |
| `klaviyo/__init__.py` | empty package marker |
| `klaviyo/utils/__init__.py` | empty package marker |
| `klaviyo/utils/client.py` | `KlaviyoClient`, `KlaviyoAPIError`, `ResourceNotFoundError`, `check_errors` |
| `klaviyo/utils/cli.py` | `add_common_flags`, `add_klaviyo_flags`, `configure_logging_from_args`, `format_output` |
| `klaviyo/scripts/__init__.py` | empty |
| `klaviyo/scripts/profiles/__init__.py` | empty |
| `klaviyo/scripts/profiles/list.py` | `GET /profiles` — filters `--email`/`--list-id`/`--segment-id`, pagination |
| `klaviyo/scripts/profiles/get.py` | `GET /profiles/{id}` or by `--email` |
| `klaviyo/scripts/profiles/create.py` | `POST /profiles` (`--dry-run`) |
| `klaviyo/scripts/profiles/update.py` | `PATCH /profiles/{id}` (`--dry-run`) |
| `klaviyo/scripts/profiles/subscribe.py` | `POST /profile-subscription-bulk-create-jobs` (`--dry-run`) |
| `klaviyo/scripts/profiles/unsubscribe.py` | `POST /profile-subscription-bulk-delete-jobs` (`--dry-run`, `--yes`) |
| `klaviyo/scripts/lists/__init__.py` | empty |
| `klaviyo/scripts/lists/list.py` | `GET /lists` |
| `klaviyo/scripts/lists/get.py` | `GET /lists/{id}` (+ `/profiles` with `--with-members`) |
| `klaviyo/scripts/lists/create.py` | `POST /lists` (`--dry-run`) |
| `klaviyo/scripts/lists/update.py` | `PATCH /lists/{id}` (`--dry-run`) |
| `klaviyo/scripts/lists/delete.py` | `DELETE /lists/{id}` (`--dry-run`, `--yes`) |
| `klaviyo/scripts/lists/add_profiles.py` | `POST /lists/{id}/relationships/profiles` (`--dry-run`) |
| `klaviyo/scripts/lists/remove_profiles.py` | `DELETE /lists/{id}/relationships/profiles` (`--dry-run`, `--yes`) |
| `klaviyo/scripts/segments/__init__.py` | empty |
| `klaviyo/scripts/segments/list.py` | `GET /segments` |
| `klaviyo/scripts/segments/get.py` | `GET /segments/{id}` (+ `/profiles` with `--with-members`) |
| `tests/klaviyo/__init__.py` | empty |
| `tests/klaviyo/utils/__init__.py` | empty |
| `tests/klaviyo/utils/test_client.py` | `KlaviyoClient` unit tests (auth, revision, pagination, check_errors, 204) |
| `tests/klaviyo/scripts/__init__.py` | empty |
| `tests/klaviyo/scripts/test_profiles_*.py` | profiles script tests |
| `tests/klaviyo/scripts/test_lists_*.py` | lists script tests |
| `tests/klaviyo/scripts/test_segments_*.py` | segments script tests |
| `skills/klaviyo-profiles/SKILL.md` | profiles + segments cluster skill |
| `skills/klaviyo-lists/SKILL.md` | lists cluster skill |

---

## Task 1: Packaging, config, and CI wiring

**Files:**
- Modify: `pyproject.toml`
- Modify: `store-config.example.yaml`
- Modify: `.github/workflows/ci.yml`
- Create: `klaviyo/__init__.py`
- Create: `klaviyo/utils/__init__.py`
- Create: `klaviyo/scripts/__init__.py`

- [ ] **Step 1: Populate the `klaviyo` extra.** Edit `pyproject.toml`, replacing the empty `klaviyo` extra with the same base deps the `shopify` extra uses:

```toml
klaviyo         = ["httpx>=0.27", "pyyaml>=6", "pydantic>=2.7"]
```

- [ ] **Step 2: Verify it installs.**

```bash
uv sync --extra dev --extra klaviyo
```
Expected: resolves and installs with no error (httpx/pyyaml/pydantic already present from `shopify`/`webhooks`).

- [ ] **Step 3: Wire `domains.klaviyo` in the example config.** Edit `store-config.example.yaml`, replacing the `klaviyo` line so it carries the dated revision in `api_version`:

```yaml
  klaviyo:        { enabled: false, api_version: "2024-10-15" }
```

- [ ] **Step 4: Add the `klaviyo` extra to CI.** Edit `.github/workflows/ci.yml`, changing the `Sync deps` step:

```yaml
      - name: Sync deps
        run: uv sync --extra dev --extra shopify --extra webhooks --extra klaviyo
```

- [ ] **Step 5: Create the empty package markers.**

```bash
mkdir -p klaviyo/utils klaviyo/scripts
touch klaviyo/__init__.py klaviyo/utils/__init__.py klaviyo/scripts/__init__.py
```

- [ ] **Step 6: Commit.**

```bash
git add pyproject.toml store-config.example.yaml .github/workflows/ci.yml klaviyo/__init__.py klaviyo/utils/__init__.py klaviyo/scripts/__init__.py
git commit -m "feat(klaviyo): populate klaviyo extra, wire config + CI, package skeleton"
```

---

## Task 2: `klaviyo/utils/client.py` — KlaviyoClient

**Files:**
- Create: `klaviyo/utils/client.py`
- Create: `tests/klaviyo/__init__.py`
- Create: `tests/klaviyo/utils/__init__.py`
- Create: `tests/klaviyo/utils/test_client.py`

- [ ] **Step 1: Create the test package markers.**

```bash
mkdir -p tests/klaviyo/utils
touch tests/klaviyo/__init__.py tests/klaviyo/utils/__init__.py
```

- [ ] **Step 2: Write failing tests.** Write `tests/klaviyo/utils/test_client.py`. These mock the underlying `HttpClient` by patching the attribute `KlaviyoClient._http` after construction (construction itself only needs the secret + config), so no real HTTP happens.

```python
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from klaviyo.utils.client import (
    KlaviyoAPIError,
    KlaviyoClient,
    ResourceNotFoundError,
    check_errors,
)


def _config(api_version="2024-10-15"):
    domain = SimpleNamespace(enabled=True, api_version=api_version)
    store = SimpleNamespace(shopify_domain="example-store.myshopify.com")
    return SimpleNamespace(store=store, domains={"klaviyo": domain})


def _response(json_body, status_code=200):
    resp = MagicMock()
    resp.json.return_value = json_body
    resp.status_code = status_code
    return resp


def test_client_sets_auth_and_revision_headers(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    captured = {}

    def fake_http(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    monkeypatch.setattr("klaviyo.utils.client.HttpClient", fake_http)
    KlaviyoClient(config=_config())
    headers = captured["default_headers"]
    assert headers["Authorization"] == "Klaviyo-API-Key pk_examplefixturekey"
    assert headers["revision"] == "2024-10-15"
    assert headers["accept"] == "application/vnd.api+json"
    assert headers["content-type"] == "application/vnd.api+json"


def test_client_revision_override_wins(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    captured = {}
    monkeypatch.setattr(
        "klaviyo.utils.client.HttpClient",
        lambda **kw: captured.update(kw) or MagicMock(),
    )
    KlaviyoClient(config=_config(api_version=None), revision="2099-01-01")
    assert captured["default_headers"]["revision"] == "2099-01-01"


def test_client_revision_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    captured = {}
    monkeypatch.setattr(
        "klaviyo.utils.client.HttpClient",
        lambda **kw: captured.update(kw) or MagicMock(),
    )
    from klaviyo.utils.client import _DEFAULT_REVISION

    KlaviyoClient(config=_config(api_version=None))
    assert captured["default_headers"]["revision"] == _DEFAULT_REVISION


def test_get_returns_parsed_body(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    client = KlaviyoClient(config=_config())
    client._http = MagicMock()
    client._http.get.return_value = _response({"data": [{"id": "p1"}]})
    body = client.get("profiles", params={"page[size]": 50})
    assert body == {"data": [{"id": "p1"}]}
    client._http.get.assert_called_once()


def test_delete_204_returns_empty(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    client = KlaviyoClient(config=_config())
    resp = MagicMock()
    resp.status_code = 204
    client._http = MagicMock()
    client._http.delete.return_value = resp
    assert client.delete("lists/abc") == {}


def test_paginate_follows_links_next(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    client = KlaviyoClient(config=_config())
    page1 = _response(
        {
            "data": [{"id": "a"}, {"id": "b"}],
            "links": {"next": "https://a.klaviyo.com/api/profiles?page[cursor]=NEXT"},
        }
    )
    page2 = _response({"data": [{"id": "c"}], "links": {"next": None}})
    client._http = MagicMock()
    client._http.get.side_effect = [page1, page2]
    items = list(client.paginate("profiles"))
    assert [i["id"] for i in items] == ["a", "b", "c"]
    assert client._http.get.call_count == 2


def test_paginate_respects_limit(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    client = KlaviyoClient(config=_config())
    page = _response(
        {
            "data": [{"id": str(n)} for n in range(50)],
            "links": {"next": "https://a.klaviyo.com/api/profiles?page[cursor]=NEXT"},
        }
    )
    client._http = MagicMock()
    client._http.get.return_value = page
    items = list(client.paginate("profiles", limit=10))
    assert len(items) == 10


def test_check_errors_raises_on_jsonapi_errors():
    body = {
        "errors": [
            {"detail": "Invalid email", "source": {"pointer": "/data/attributes/email"}}
        ]
    }
    with pytest.raises(KlaviyoAPIError) as exc:
        check_errors(body)
    assert "Invalid email" in str(exc.value)
    assert "/data/attributes/email" in str(exc.value)
    assert exc.value.errors == body["errors"]


def test_check_errors_noop_on_clean_body():
    check_errors({"data": {"id": "p1"}})  # no raise


def test_resource_not_found_is_lookup_error():
    assert issubclass(ResourceNotFoundError, LookupError)
```

- [ ] **Step 3: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/utils/test_client.py -v
```
Expected: collection/import error — `ModuleNotFoundError: No module named 'klaviyo.utils.client'`.

- [ ] **Step 4: Implement `klaviyo/utils/client.py`.** Complete code:

```python
"""Klaviyo JSON:API client built on core.http.HttpClient.

Mirrors shopify.utils.client.ShopifyClient: reads its secret at construction,
sends domain auth + the dated ``revision`` header, exposes thin verb wrappers
over core.http.HttpClient (which retries 429/5xx), and is a context manager.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from core.config import StoreConfig
from core.http import HttpClient
from core.logging import get_logger
from core.secrets import require_secret

_log = get_logger("ecom.klaviyo.client")

_BASE_URL = "https://a.klaviyo.com/api/"

# Known-good dated revision used when domains.klaviyo.api_version is unset.
# Override per-invocation with --revision (see klaviyo.utils.cli.add_klaviyo_flags).
_DEFAULT_REVISION = "2024-10-15"


class KlaviyoAPIError(RuntimeError):
    """Raised when a JSON:API response carries a non-empty top-level ``errors`` array.

    Carries the raw ``errors`` list and the optional parsed ``body`` so callers
    can inspect partial results. Analogous to Shopify's user-error handling.
    """

    def __init__(
        self,
        message: str,
        *,
        errors: list[dict] | None = None,
        body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.errors = errors or []
        self.body = body


class ResourceNotFoundError(LookupError):
    """Raised when a lookup (e.g. profile by email) returns zero results.

    Subclasses LookupError per stdlib convention, mirroring Shopify's
    SkuNotFoundError.
    """

    def __init__(self, what: str) -> None:
        self.what = what
        super().__init__(f"{what} not found")


def check_errors(body: dict[str, Any] | None) -> None:
    """Raise KlaviyoAPIError if ``body['errors']`` is a non-empty list.

    Summarizes each error's ``detail`` and, when present, its
    ``source.pointer``. Free function for direct import:
        from klaviyo.utils.client import check_errors
    """
    if not body:
        return
    errors = body.get("errors") or []
    if not errors:
        return
    parts = []
    for err in errors:
        detail = err.get("detail") or err.get("title") or "?"
        pointer = (err.get("source") or {}).get("pointer")
        parts.append(f"{detail} ({pointer})" if pointer else detail)
    raise KlaviyoAPIError("; ".join(parts), errors=errors, body=body)


class KlaviyoClient:
    """Klaviyo JSON:API client.

    Reads KLAVIYO_PRIVATE_API_KEY from the environment at construction time.
    The dated ``revision`` header comes from config.domains['klaviyo'].api_version,
    falling back to _DEFAULT_REVISION, overridable via the ``revision`` argument.
    """

    def __init__(self, config: StoreConfig, *, revision: str | None = None) -> None:
        self._config = config
        key = require_secret("KLAVIYO_PRIVATE_API_KEY")
        domain = config.domains.get("klaviyo")
        configured = domain.api_version if domain else None
        self._revision = revision or configured or _DEFAULT_REVISION
        self._http = HttpClient(
            base_url=_BASE_URL,
            default_headers={
                "Authorization": f"Klaviyo-API-Key {key}",
                "revision": self._revision,
                "accept": "application/vnd.api+json",
                "content-type": "application/vnd.api+json",
            },
        )

    @property
    def revision(self) -> str:
        return self._revision

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._http.get(path, params=params)
        return response.json()

    def post(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._http.post(path, json=json)
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def patch(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._http.patch(path, json=json)
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def delete(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._http.delete(path, json=json) if json else self._http.delete(path)
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def paginate(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        limit: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield ``data[]`` items across pages by following ``links.next``.

        Klaviyo uses cursor pagination; ``links.next`` is a fully-qualified URL,
        so subsequent requests pass it through unchanged. When ``limit`` is set,
        stops after yielding that many items (logs a truncation notice).
        """
        next_url: str | None = path
        first = True
        yielded = 0
        while next_url:
            body = self.get(next_url, params=params if first else None)
            first = False
            check_errors(body)
            for item in body.get("data") or []:
                if limit is not None and yielded >= limit:
                    _log.info("paginate truncated at limit=%d for %s", limit, path)
                    return
                yield item
                yielded += 1
            next_url = (body.get("links") or {}).get("next")

    def __enter__(self) -> KlaviyoClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()
```

- [ ] **Step 5: Run, confirm pass.**

```bash
uv run pytest tests/klaviyo/utils/test_client.py -v
```
Expected: all tests pass.

- [ ] **Step 6: Ruff + commit.**

```bash
uv run ruff check klaviyo/utils/client.py tests/klaviyo/utils/test_client.py
uv run ruff format klaviyo/utils/client.py tests/klaviyo/utils/test_client.py
git add klaviyo/utils/client.py tests/klaviyo/__init__.py tests/klaviyo/utils/
git commit -m "feat(klaviyo): KlaviyoClient (auth, revision, pagination, check_errors)"
```

---

## Task 3: `klaviyo/utils/cli.py` — CLI helpers

**Files:**
- Create: `klaviyo/utils/cli.py`
- Create: `tests/klaviyo/utils/test_cli.py`

- [ ] **Step 1: Write failing tests.** Write `tests/klaviyo/utils/test_cli.py`:

```python
import argparse
import json

from klaviyo.utils import cli


def _parsed(argv):
    parser = argparse.ArgumentParser()
    cli.add_common_flags(parser)
    cli.add_klaviyo_flags(parser)
    return parser.parse_args(argv)


def test_common_flag_defaults():
    args = _parsed([])
    assert args.output == "table"
    assert args.limit == 50
    assert args.config == "store-config.yaml"
    assert args.dry_run is False
    assert args.verbose is False


def test_klaviyo_flags_revision_and_yes():
    args = _parsed(["--revision", "2099-01-01", "--yes"])
    assert args.revision == "2099-01-01"
    assert args.yes is True


def test_klaviyo_flag_defaults():
    args = _parsed([])
    assert args.revision is None
    assert args.yes is False


def test_format_output_json():
    out = cli.format_output([{"id": "p1", "email": "a@b.com"}], "json")
    assert json.loads(out) == [{"id": "p1", "email": "a@b.com"}]


def test_format_output_table_renders_rows():
    out = cli.format_output([{"id": "p1", "email": "a@b.com"}], "table")
    assert "id" in out and "email" in out and "p1" in out


def test_format_output_empty_table():
    assert cli.format_output([], "table") == "(no rows)"
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/utils/test_cli.py -v
```
Expected: `ModuleNotFoundError: No module named 'klaviyo.utils.cli'`.

- [ ] **Step 3: Implement `klaviyo/utils/cli.py`.** Near-copy of `shopify/utils/cli.py` plus `add_klaviyo_flags`. Complete code:

```python
"""Shared argparse + output helpers for klaviyo/scripts/.

A near-copy of shopify/utils/cli.py (duplicated rather than imported to avoid
coupling two domains; promoting to core/cli.py is a deferred follow-up — spec
§3.2). Adds add_klaviyo_flags for the domain-specific --revision/--yes flags.
"""

from __future__ import annotations

import argparse
import json
import logging
from typing import Any


def add_common_flags(parser: argparse.ArgumentParser) -> None:
    """Register the conventions every klaviyo/scripts/* script supports."""
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip writes; exercise read path",
    )
    parser.add_argument(
        "--output",
        choices=("table", "json", "markdown"),
        default="table",
    )
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--config", default="store-config.yaml")
    parser.add_argument("--verbose", action="store_true")


def add_klaviyo_flags(parser: argparse.ArgumentParser) -> None:
    """Register Klaviyo-specific flags.

    --revision overrides the dated API revision the client otherwise reads from
    domains.klaviyo.api_version. --yes confirms high-stakes operations.
    """
    parser.add_argument(
        "--revision",
        default=None,
        help="Override the dated Klaviyo API revision (default: config api_version)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm a high-stakes operation (required for live execution)",
    )


def configure_logging_from_args(args: argparse.Namespace) -> None:
    """Honor --verbose by raising the ecom.* logger to DEBUG."""
    if getattr(args, "verbose", False):
        logging.getLogger("ecom").setLevel(logging.DEBUG)


def format_output(data: Any, fmt: str) -> str:
    """Format data as a table (default), JSON, or Markdown table."""
    if fmt == "json":
        return json.dumps(data, indent=2, default=str)
    if fmt == "markdown":
        if isinstance(data, list):
            return _markdown_table(data)
        return f"```json\n{json.dumps(data, indent=2, default=str)}\n```"
    if isinstance(data, list):
        return _plain_table(data)
    return json.dumps(data, indent=2, default=str)


def _plain_table(rows: list[dict]) -> str:
    if not rows:
        return "(no rows)"
    cols = list(rows[0].keys())
    widths = {c: max(len(c), max((len(str(r.get(c, ""))) for r in rows), default=0)) for c in cols}
    header = " | ".join(c.ljust(widths[c]) for c in cols)
    sep = "-+-".join("-" * widths[c] for c in cols)
    body = "\n".join(" | ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols) for r in rows)
    return f"{header}\n{sep}\n{body}"


def _markdown_table(rows: list[dict]) -> str:
    if not rows:
        return "_(no rows)_"
    cols = list(rows[0].keys())
    head = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    body = "\n".join("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |" for r in rows)
    return f"{head}\n{sep}\n{body}"
```

- [ ] **Step 4: Run, confirm pass.**

```bash
uv run pytest tests/klaviyo/utils/test_cli.py -v
```
Expected: all tests pass.

- [ ] **Step 5: Ruff + commit.**

```bash
uv run ruff check klaviyo/utils/cli.py tests/klaviyo/utils/test_cli.py
uv run ruff format klaviyo/utils/cli.py tests/klaviyo/utils/test_cli.py
git add klaviyo/utils/cli.py tests/klaviyo/utils/test_cli.py
git commit -m "feat(klaviyo): cli helpers (add_common_flags, add_klaviyo_flags, format_output)"
```

---

## Task 4: `profiles/list.py` (reference read script)

This is the first script of the profiles resource and the template for every read script: flatten JSON:API resources into flat rows, build filter params, use `paginate` capped by `--limit`.

**Files:**
- Create: `klaviyo/scripts/profiles/__init__.py`
- Create: `klaviyo/scripts/profiles/list.py`
- Create: `tests/klaviyo/scripts/__init__.py`
- Create: `tests/klaviyo/scripts/test_profiles_list.py`

- [ ] **Step 1: Create test/script package markers.**

```bash
mkdir -p klaviyo/scripts/profiles tests/klaviyo/scripts
touch klaviyo/scripts/profiles/__init__.py tests/klaviyo/scripts/__init__.py
```

- [ ] **Step 2: Write failing test.** Write `tests/klaviyo/scripts/test_profiles_list.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.profiles import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.profiles.list.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.profiles.list.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_profiles_list_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [
                {
                    "id": "01H",
                    "type": "profile",
                    "attributes": {
                        "email": "a@b.com",
                        "first_name": "Ada",
                        "last_name": "Lovelace",
                    },
                }
            ]
        )
        with patch.object(sys, "argv", ["list.py", "--output", "json"]):
            assert listcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "01H"
    assert parsed[0]["email"] == "a@b.com"
    assert parsed[0]["first_name"] == "Ada"


def test_profiles_list_email_filter_builds_param(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py", "--email", "a@b.com"]):
            assert listcmd.main() == 0
        _, kwargs = client.paginate.call_args
        params = kwargs.get("params") or client.paginate.call_args[0][1]
        assert params["filter"] == 'equals(email,"a@b.com")'


def test_profiles_list_passes_limit(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py", "--limit", "5"]):
            assert listcmd.main() == 0
        _, kwargs = client.paginate.call_args
        assert kwargs["limit"] == 5
```

- [ ] **Step 3: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_profiles_list.py -v
```
Expected: `ModuleNotFoundError: No module named 'klaviyo.scripts.profiles.list'`.

- [ ] **Step 4: Implement `klaviyo/scripts/profiles/list.py`.** Complete code:

```python
"""List Klaviyo profiles with optional filters.

Filters: --email (exact), --list-id (membership), --segment-id (membership).
Flattens JSON:API profile resources into flat rows (id + common attributes).
Honors --limit via the client's cursor pagination.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from klaviyo.utils.cli import (
    add_common_flags,
    add_klaviyo_flags,
    configure_logging_from_args,
    format_output,
)
from klaviyo.utils.client import KlaviyoClient


def _flatten(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "email": attrs.get("email"),
        "phone_number": attrs.get("phone_number"),
        "first_name": attrs.get("first_name"),
        "last_name": attrs.get("last_name"),
        "created": attrs.get("created"),
        "updated": attrs.get("updated"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Klaviyo profiles.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--email", help="Filter to the profile with this exact email")
    parser.add_argument("--list-id", dest="list_id", help="List membership to filter by")
    parser.add_argument(
        "--segment-id", dest="segment_id", help="Segment membership to filter by"
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    path = "profiles"
    params: dict[str, object] = {}
    if args.email:
        params["filter"] = f'equals(email,"{args.email}")'
    if args.list_id:
        path = f"lists/{args.list_id}/profiles"
    if args.segment_id:
        path = f"segments/{args.segment_id}/profiles"

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        rows = [_flatten(r) for r in client.paginate(path, params=params, limit=args.limit)]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run, confirm pass.**

```bash
uv run pytest tests/klaviyo/scripts/test_profiles_list.py -v
```
Expected: all tests pass.

- [ ] **Step 6: Ruff + commit.**

```bash
uv run ruff check klaviyo/scripts/profiles/list.py tests/klaviyo/scripts/test_profiles_list.py
uv run ruff format klaviyo/scripts/profiles/list.py tests/klaviyo/scripts/test_profiles_list.py
git add klaviyo/scripts/profiles/__init__.py klaviyo/scripts/profiles/list.py tests/klaviyo/scripts/__init__.py tests/klaviyo/scripts/test_profiles_list.py
git commit -m "feat(klaviyo): profiles/list.py with email/list/segment filters"
```

---

## Task 5: `profiles/get.py`

`GET /profiles/{id}` or, when `--email` is given, resolve via `GET /profiles?filter=equals(email,...)` and raise `ResourceNotFoundError` on zero matches.

**Files:**
- Create: `klaviyo/scripts/profiles/get.py`
- Create: `tests/klaviyo/scripts/test_profiles_get.py`

- [ ] **Step 1: Write failing test.** Write `tests/klaviyo/scripts/test_profiles_get.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from klaviyo.scripts.profiles import get as getcmd
from klaviyo.utils.client import ResourceNotFoundError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.profiles.get.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.profiles.get.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_get_by_id(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "data": {"id": "01H", "type": "profile", "attributes": {"email": "a@b.com"}}
        }
        with patch.object(sys, "argv", ["get.py", "--id", "01H", "--output", "json"]):
            assert getcmd.main() == 0
        client.get.assert_called_once_with("profiles/01H")
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "01H"
    assert parsed["email"] == "a@b.com"


def test_get_by_email_resolves(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "data": [{"id": "01H", "type": "profile", "attributes": {"email": "a@b.com"}}]
        }
        with patch.object(sys, "argv", ["get.py", "--email", "a@b.com", "--output", "json"]):
            assert getcmd.main() == 0
        _, kwargs = client.get.call_args
        assert kwargs["params"]["filter"] == 'equals(email,"a@b.com")'
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "01H"


def test_get_by_email_not_found_raises(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {"data": []}
        with (
            patch.object(sys, "argv", ["get.py", "--email", "missing@b.com"]),
            pytest.raises(ResourceNotFoundError),
        ):
            getcmd.main()


def test_get_requires_id_or_email(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with (
            patch.object(sys, "argv", ["get.py"]),
            pytest.raises(SystemExit),
        ):
            getcmd.main()
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_profiles_get.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `klaviyo/scripts/profiles/get.py`.** Complete code:

```python
"""Get a single Klaviyo profile by --id or by --email.

By email, resolves via a filtered list query and raises ResourceNotFoundError
when no profile matches.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from klaviyo.utils.cli import (
    add_common_flags,
    add_klaviyo_flags,
    configure_logging_from_args,
    format_output,
)
from klaviyo.utils.client import KlaviyoClient, ResourceNotFoundError, check_errors


def _flatten(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "email": attrs.get("email"),
        "phone_number": attrs.get("phone_number"),
        "first_name": attrs.get("first_name"),
        "last_name": attrs.get("last_name"),
        "created": attrs.get("created"),
        "updated": attrs.get("updated"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get a Klaviyo profile by id or email.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", help="Profile id")
    parser.add_argument("--email", help="Profile email (resolved to id)")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if not args.id and not args.email:
        parser.error("one of --id or --email is required")

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        if args.id:
            body = client.get(f"profiles/{args.id}")
            check_errors(body)
            resource = body.get("data") or {}
        else:
            body = client.get(
                "profiles", params={"filter": f'equals(email,"{args.email}")'}
            )
            check_errors(body)
            data = body.get("data") or []
            if not data:
                raise ResourceNotFoundError(f"profile with email {args.email!r}")
            resource = data[0]

    print(format_output(_flatten(resource), args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_profiles_get.py -v
uv run ruff check klaviyo/scripts/profiles/get.py tests/klaviyo/scripts/test_profiles_get.py
uv run ruff format klaviyo/scripts/profiles/get.py tests/klaviyo/scripts/test_profiles_get.py
git add klaviyo/scripts/profiles/get.py tests/klaviyo/scripts/test_profiles_get.py
git commit -m "feat(klaviyo): profiles/get.py by id or email"
```

---

## Task 6: `profiles/create.py` (reference mutation script)

First mutation script — the template for all mutations: build the JSON:API body, `--dry-run` prints it and returns 0 without calling the API, else POST + `check_errors` + flatten.

**Files:**
- Create: `klaviyo/scripts/profiles/create.py`
- Create: `tests/klaviyo/scripts/test_profiles_create.py`

- [ ] **Step 1: Write failing test.** Write `tests/klaviyo/scripts/test_profiles_create.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from klaviyo.scripts.profiles import create as createcmd
from klaviyo.utils.client import KlaviyoAPIError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.profiles.create.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.profiles.create.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_create_dry_run_prints_body_and_skips_post(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "create.py",
                "--email",
                "a@b.com",
                "--first-name",
                "Ada",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "profile"
    assert parsed["data"]["attributes"]["email"] == "a@b.com"
    assert parsed["data"]["attributes"]["first_name"] == "Ada"


def test_create_posts_jsonapi_body(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {
            "data": {"id": "01H", "type": "profile", "attributes": {"email": "a@b.com"}}
        }
        with patch.object(sys, "argv", ["create.py", "--email", "a@b.com"]):
            assert createcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "profiles"
        body = kwargs.get("json") or args[1]
        assert body["data"]["attributes"]["email"] == "a@b.com"


def test_create_surfaces_api_error(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {
            "errors": [{"detail": "duplicate profile", "source": {"pointer": "/data"}}]
        }
        with (
            patch.object(sys, "argv", ["create.py", "--email", "a@b.com"]),
            pytest.raises(KlaviyoAPIError),
        ):
            createcmd.main()
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_profiles_create.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `klaviyo/scripts/profiles/create.py`.** Complete code:

```python
"""Create a Klaviyo profile.

Builds a JSON:API ``profile`` resource from the given attributes. --dry-run
prints the request body and skips the POST.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from klaviyo.utils.cli import (
    add_common_flags,
    add_klaviyo_flags,
    configure_logging_from_args,
    format_output,
)
from klaviyo.utils.client import KlaviyoClient, check_errors


def _build_body(args: argparse.Namespace) -> dict:
    attributes: dict[str, object] = {}
    if args.email:
        attributes["email"] = args.email
    if args.phone_number:
        attributes["phone_number"] = args.phone_number
    if args.first_name:
        attributes["first_name"] = args.first_name
    if args.last_name:
        attributes["last_name"] = args.last_name
    return {"data": {"type": "profile", "attributes": attributes}}


def _flatten(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "email": attrs.get("email"),
        "first_name": attrs.get("first_name"),
        "last_name": attrs.get("last_name"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a Klaviyo profile.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--email", help="Profile email")
    parser.add_argument("--phone-number", dest="phone_number", help="E.164 phone number")
    parser.add_argument("--first-name", dest="first_name")
    parser.add_argument("--last-name", dest="last_name")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if not args.email and not args.phone_number:
        parser.error("at least one of --email or --phone-number is required")

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("profiles", json=body)

    check_errors(result)
    print(format_output(_flatten(result.get("data") or {}), args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_profiles_create.py -v
uv run ruff check klaviyo/scripts/profiles/create.py tests/klaviyo/scripts/test_profiles_create.py
uv run ruff format klaviyo/scripts/profiles/create.py tests/klaviyo/scripts/test_profiles_create.py
git add klaviyo/scripts/profiles/create.py tests/klaviyo/scripts/test_profiles_create.py
git commit -m "feat(klaviyo): profiles/create.py with --dry-run"
```

---

## Task 7: `profiles/update.py`

`PATCH /profiles/{id}`. JSON:API update bodies require the `id` inside `data`. `--dry-run` prints the body.

**Files:**
- Create: `klaviyo/scripts/profiles/update.py`
- Create: `tests/klaviyo/scripts/test_profiles_update.py`

- [ ] **Step 1: Write failing test.** Write `tests/klaviyo/scripts/test_profiles_update.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.profiles import update as updatecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.profiles.update.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.profiles.update.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_update_dry_run_includes_id(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["update.py", "--id", "01H", "--first-name", "Ada", "--dry-run", "--output", "json"],
        ):
            assert updatecmd.main() == 0
        assert client.patch.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["id"] == "01H"
    assert parsed["data"]["type"] == "profile"
    assert parsed["data"]["attributes"]["first_name"] == "Ada"


def test_update_patches_path_with_id(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.patch.return_value = {
            "data": {"id": "01H", "type": "profile", "attributes": {"first_name": "Ada"}}
        }
        with patch.object(sys, "argv", ["update.py", "--id", "01H", "--first-name", "Ada"]):
            assert updatecmd.main() == 0
        args, kwargs = client.patch.call_args
        assert args[0] == "profiles/01H"
        body = kwargs.get("json") or args[1]
        assert body["data"]["id"] == "01H"
        assert body["data"]["attributes"]["first_name"] == "Ada"
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_profiles_update.py -v
```

- [ ] **Step 3: Implement `klaviyo/scripts/profiles/update.py`.** Complete code:

```python
"""Update a Klaviyo profile by id.

JSON:API update bodies carry the resource id inside ``data``. --dry-run prints
the body and skips the PATCH.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from klaviyo.utils.cli import (
    add_common_flags,
    add_klaviyo_flags,
    configure_logging_from_args,
    format_output,
)
from klaviyo.utils.client import KlaviyoClient, check_errors


def _build_body(args: argparse.Namespace) -> dict:
    attributes: dict[str, object] = {}
    if args.email:
        attributes["email"] = args.email
    if args.phone_number:
        attributes["phone_number"] = args.phone_number
    if args.first_name:
        attributes["first_name"] = args.first_name
    if args.last_name:
        attributes["last_name"] = args.last_name
    return {"data": {"type": "profile", "id": args.id, "attributes": attributes}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update a Klaviyo profile by id.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Profile id")
    parser.add_argument("--email")
    parser.add_argument("--phone-number", dest="phone_number")
    parser.add_argument("--first-name", dest="first_name")
    parser.add_argument("--last-name", dest="last_name")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.patch(f"profiles/{args.id}", json=body)

    check_errors(result)
    resource = result.get("data") or {}
    attrs = resource.get("attributes") or {}
    print(
        format_output(
            {
                "id": resource.get("id"),
                "email": attrs.get("email"),
                "first_name": attrs.get("first_name"),
                "last_name": attrs.get("last_name"),
            },
            args.output,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_profiles_update.py -v
uv run ruff check klaviyo/scripts/profiles/update.py tests/klaviyo/scripts/test_profiles_update.py
uv run ruff format klaviyo/scripts/profiles/update.py tests/klaviyo/scripts/test_profiles_update.py
git add klaviyo/scripts/profiles/update.py tests/klaviyo/scripts/test_profiles_update.py
git commit -m "feat(klaviyo): profiles/update.py with --dry-run"
```

---

## Task 8: `profiles/subscribe.py`

`POST /profile-subscription-bulk-create-jobs`. Sets marketing consent for a profile on a list. `--dry-run` prints the body. Not `--yes`-gated (consent opt-in is low-risk; only the unsubscribe op is gated, per spec §4).

**Files:**
- Create: `klaviyo/scripts/profiles/subscribe.py`
- Create: `tests/klaviyo/scripts/test_profiles_subscribe.py`

- [ ] **Step 1: Write failing test.** Write `tests/klaviyo/scripts/test_profiles_subscribe.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.profiles import subscribe as subcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.profiles.subscribe.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.profiles.subscribe.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_subscribe_dry_run_builds_job_body(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "subscribe.py",
                "--email",
                "a@b.com",
                "--list-id",
                "LST1",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert subcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "profile-subscription-bulk-create-job"
    assert parsed["data"]["relationships"]["list"]["data"]["id"] == "LST1"
    profile = parsed["data"]["attributes"]["profiles"]["data"][0]
    assert profile["attributes"]["email"] == "a@b.com"


def test_subscribe_posts_to_job_endpoint(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {}
        with patch.object(
            sys, "argv", ["subscribe.py", "--email", "a@b.com", "--list-id", "LST1"]
        ):
            assert subcmd.main() == 0
        args, _ = client.post.call_args
        assert args[0] == "profile-subscription-bulk-create-jobs"
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_profiles_subscribe.py -v
```

- [ ] **Step 3: Implement `klaviyo/scripts/profiles/subscribe.py`.** Complete code:

```python
"""Subscribe a profile to marketing on a list (consent opt-in).

Builds a profile-subscription-bulk-create-job for a single profile. --dry-run
prints the body and skips the POST.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from klaviyo.utils.cli import (
    add_common_flags,
    add_klaviyo_flags,
    configure_logging_from_args,
    format_output,
)
from klaviyo.utils.client import KlaviyoClient, check_errors


def _build_body(args: argparse.Namespace) -> dict:
    profile_attrs: dict[str, object] = {}
    if args.email:
        profile_attrs["email"] = args.email
        profile_attrs["subscriptions"] = {"email": {"marketing": {"consent": "SUBSCRIBED"}}}
    if args.phone_number:
        profile_attrs["phone_number"] = args.phone_number
        profile_attrs.setdefault("subscriptions", {})["sms"] = {
            "marketing": {"consent": "SUBSCRIBED"}
        }
    return {
        "data": {
            "type": "profile-subscription-bulk-create-job",
            "attributes": {
                "profiles": {
                    "data": [{"type": "profile", "attributes": profile_attrs}]
                }
            },
            "relationships": {"list": {"data": {"type": "list", "id": args.list_id}}},
        }
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Subscribe a profile to a list's marketing.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--list-id", dest="list_id", required=True, help="List id")
    parser.add_argument("--email", help="Profile email")
    parser.add_argument("--phone-number", dest="phone_number", help="E.164 phone number")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if not args.email and not args.phone_number:
        parser.error("at least one of --email or --phone-number is required")

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("profile-subscription-bulk-create-jobs", json=body)

    check_errors(result)
    print(f"Subscribed to list {args.list_id} (job accepted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_profiles_subscribe.py -v
uv run ruff check klaviyo/scripts/profiles/subscribe.py tests/klaviyo/scripts/test_profiles_subscribe.py
uv run ruff format klaviyo/scripts/profiles/subscribe.py tests/klaviyo/scripts/test_profiles_subscribe.py
git add klaviyo/scripts/profiles/subscribe.py tests/klaviyo/scripts/test_profiles_subscribe.py
git commit -m "feat(klaviyo): profiles/subscribe.py with --dry-run"
```

---

## Task 9: `profiles/unsubscribe.py` (reference gated mutation)

`POST /profile-subscription-bulk-delete-jobs`. High-stakes: `--yes`-gated. `--dry-run` works without `--yes`; live execution without `--yes` errors via `parser.error(...)` before any network call (mirrors `webhooks/delete.py`).

**Files:**
- Create: `klaviyo/scripts/profiles/unsubscribe.py`
- Create: `tests/klaviyo/scripts/test_profiles_unsubscribe.py`

- [ ] **Step 1: Write failing test.** Write `tests/klaviyo/scripts/test_profiles_unsubscribe.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.profiles import unsubscribe as unsubcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.profiles.unsubscribe.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.profiles.unsubscribe.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_unsubscribe_dry_run_skips_post_without_yes(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["unsubscribe.py", "--email", "a@b.com", "--list-id", "LST1", "--dry-run", "--output", "json"],
        ):
            assert unsubcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "profile-subscription-bulk-delete-job"


def test_unsubscribe_without_yes_errors_in_live_mode(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["unsubscribe.py", "--email", "a@b.com", "--list-id", "LST1"]
        ):
            try:
                rc = unsubcmd.main()
            except SystemExit as e:
                rc = e.code
        assert rc != 0
        assert client.post.call_count == 0


def test_unsubscribe_with_yes_posts(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {}
        with patch.object(
            sys, "argv", ["unsubscribe.py", "--email", "a@b.com", "--list-id", "LST1", "--yes"]
        ):
            assert unsubcmd.main() == 0
        args, _ = client.post.call_args
        assert args[0] == "profile-subscription-bulk-delete-jobs"
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_profiles_unsubscribe.py -v
```

- [ ] **Step 3: Implement `klaviyo/scripts/profiles/unsubscribe.py`.** Complete code:

```python
"""Unsubscribe a profile from a list's marketing (consent removal).

High-stakes: --yes is required for live execution. --dry-run works without
--yes and prints the body without calling the API.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from klaviyo.utils.cli import (
    add_common_flags,
    add_klaviyo_flags,
    configure_logging_from_args,
    format_output,
)
from klaviyo.utils.client import KlaviyoClient, check_errors


def _build_body(args: argparse.Namespace) -> dict:
    profile_attrs: dict[str, object] = {}
    if args.email:
        profile_attrs["email"] = args.email
    if args.phone_number:
        profile_attrs["phone_number"] = args.phone_number
    return {
        "data": {
            "type": "profile-subscription-bulk-delete-job",
            "attributes": {
                "profiles": {
                    "data": [{"type": "profile", "attributes": profile_attrs}]
                }
            },
            "relationships": {"list": {"data": {"type": "list", "id": args.list_id}}},
        }
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Unsubscribe a profile from a list's marketing.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--list-id", dest="list_id", required=True, help="List id")
    parser.add_argument("--email", help="Profile email")
    parser.add_argument("--phone-number", dest="phone_number", help="E.164 phone number")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if not args.email and not args.phone_number:
        parser.error("at least one of --email or --phone-number is required")

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    if not args.yes:
        parser.error("--yes is required to confirm unsubscribe; aborting")

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("profile-subscription-bulk-delete-jobs", json=body)

    check_errors(result)
    print(f"Unsubscribed from list {args.list_id} (job accepted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_profiles_unsubscribe.py -v
uv run ruff check klaviyo/scripts/profiles/unsubscribe.py tests/klaviyo/scripts/test_profiles_unsubscribe.py
uv run ruff format klaviyo/scripts/profiles/unsubscribe.py tests/klaviyo/scripts/test_profiles_unsubscribe.py
git add klaviyo/scripts/profiles/unsubscribe.py tests/klaviyo/scripts/test_profiles_unsubscribe.py
git commit -m "feat(klaviyo): profiles/unsubscribe.py gated on --yes"
```

---

## Task 10: `lists/list.py` and `lists/get.py`

**Files:**
- Create: `klaviyo/scripts/lists/__init__.py`
- Create: `klaviyo/scripts/lists/list.py`
- Create: `klaviyo/scripts/lists/get.py`
- Create: `tests/klaviyo/scripts/test_lists_list.py`
- Create: `tests/klaviyo/scripts/test_lists_get.py`

- [ ] **Step 1: Create the lists package marker.**

```bash
mkdir -p klaviyo/scripts/lists
touch klaviyo/scripts/lists/__init__.py
```

- [ ] **Step 2: Write failing tests.** Write `tests/klaviyo/scripts/test_lists_list.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.lists import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.lists.list.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.lists.list.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_lists_list_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [{"id": "LST1", "type": "list", "attributes": {"name": "Newsletter"}}]
        )
        with patch.object(sys, "argv", ["list.py", "--output", "json"]):
            assert listcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "LST1"
    assert parsed[0]["name"] == "Newsletter"
```

Write `tests/klaviyo/scripts/test_lists_get.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.lists import get as getcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.lists.get.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.lists.get.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_get_list_by_id(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "data": {"id": "LST1", "type": "list", "attributes": {"name": "Newsletter"}}
        }
        with patch.object(sys, "argv", ["get.py", "--id", "LST1", "--output", "json"]):
            assert getcmd.main() == 0
        client.get.assert_called_once_with("lists/LST1")
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "LST1"
    assert parsed["name"] == "Newsletter"


def test_get_list_with_members(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "data": {"id": "LST1", "type": "list", "attributes": {"name": "Newsletter"}}
        }
        client.paginate.return_value = iter(
            [{"id": "01H", "type": "profile", "attributes": {"email": "a@b.com"}}]
        )
        with patch.object(
            sys, "argv", ["get.py", "--id", "LST1", "--with-members", "--output", "json"]
        ):
            assert getcmd.main() == 0
        client.paginate.assert_called_once()
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["members"][0]["email"] == "a@b.com"
```

- [ ] **Step 3: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_lists_list.py tests/klaviyo/scripts/test_lists_get.py -v
```

- [ ] **Step 4: Implement `klaviyo/scripts/lists/list.py`.** Complete code:

```python
"""List Klaviyo lists.

Flattens JSON:API list resources into flat rows. Honors --limit via cursor
pagination.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from klaviyo.utils.cli import (
    add_common_flags,
    add_klaviyo_flags,
    configure_logging_from_args,
    format_output,
)
from klaviyo.utils.client import KlaviyoClient


def _flatten(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "name": attrs.get("name"),
        "created": attrs.get("created"),
        "updated": attrs.get("updated"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Klaviyo lists.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        rows = [_flatten(r) for r in client.paginate("lists", limit=args.limit)]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Implement `klaviyo/scripts/lists/get.py`.** Complete code:

```python
"""Get a Klaviyo list by id, optionally with its member profiles.

--with-members appends a paginated profile listing (capped by --limit) under a
``members`` key in the output.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from klaviyo.utils.cli import (
    add_common_flags,
    add_klaviyo_flags,
    configure_logging_from_args,
    format_output,
)
from klaviyo.utils.client import KlaviyoClient, check_errors


def _flatten_list(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "name": attrs.get("name"),
        "created": attrs.get("created"),
        "updated": attrs.get("updated"),
    }


def _flatten_profile(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "email": attrs.get("email"),
        "first_name": attrs.get("first_name"),
        "last_name": attrs.get("last_name"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get a Klaviyo list by id.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="List id")
    parser.add_argument(
        "--with-members",
        dest="with_members",
        action="store_true",
        help="Also list member profiles (capped by --limit)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        body = client.get(f"lists/{args.id}")
        check_errors(body)
        out = _flatten_list(body.get("data") or {})
        if args.with_members:
            out["members"] = [
                _flatten_profile(r)
                for r in client.paginate(f"lists/{args.id}/profiles", limit=args.limit)
            ]

    print(format_output(out, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_lists_list.py tests/klaviyo/scripts/test_lists_get.py -v
uv run ruff check klaviyo/scripts/lists/ tests/klaviyo/scripts/test_lists_list.py tests/klaviyo/scripts/test_lists_get.py
uv run ruff format klaviyo/scripts/lists/ tests/klaviyo/scripts/test_lists_list.py tests/klaviyo/scripts/test_lists_get.py
git add klaviyo/scripts/lists/__init__.py klaviyo/scripts/lists/list.py klaviyo/scripts/lists/get.py tests/klaviyo/scripts/test_lists_list.py tests/klaviyo/scripts/test_lists_get.py
git commit -m "feat(klaviyo): lists/list.py and lists/get.py (--with-members)"
```

---

## Task 11: `lists/create.py` and `lists/update.py`

Same mutation shape as `profiles/create.py`/`update.py` (JSON:API `list` resource). `--dry-run` on both.

**Files:**
- Create: `klaviyo/scripts/lists/create.py`
- Create: `klaviyo/scripts/lists/update.py`
- Create: `tests/klaviyo/scripts/test_lists_create.py`
- Create: `tests/klaviyo/scripts/test_lists_update.py`

- [ ] **Step 1: Write failing tests.** Write `tests/klaviyo/scripts/test_lists_create.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.lists import create as createcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.lists.create.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.lists.create.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_create_list_dry_run(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["create.py", "--name", "VIPs", "--dry-run", "--output", "json"]
        ):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "list"
    assert parsed["data"]["attributes"]["name"] == "VIPs"


def test_create_list_posts(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {
            "data": {"id": "LST9", "type": "list", "attributes": {"name": "VIPs"}}
        }
        with patch.object(sys, "argv", ["create.py", "--name", "VIPs"]):
            assert createcmd.main() == 0
        args, _ = client.post.call_args
        assert args[0] == "lists"
```

Write `tests/klaviyo/scripts/test_lists_update.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.lists import update as updatecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.lists.update.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.lists.update.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_update_list_dry_run_includes_id(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["update.py", "--id", "LST1", "--name", "VIP", "--dry-run", "--output", "json"]
        ):
            assert updatecmd.main() == 0
        assert client.patch.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["id"] == "LST1"
    assert parsed["data"]["attributes"]["name"] == "VIP"


def test_update_list_patches_path(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.patch.return_value = {
            "data": {"id": "LST1", "type": "list", "attributes": {"name": "VIP"}}
        }
        with patch.object(sys, "argv", ["update.py", "--id", "LST1", "--name", "VIP"]):
            assert updatecmd.main() == 0
        args, _ = client.patch.call_args
        assert args[0] == "lists/LST1"
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_lists_create.py tests/klaviyo/scripts/test_lists_update.py -v
```

- [ ] **Step 3: Implement `klaviyo/scripts/lists/create.py`.** Complete code:

```python
"""Create a Klaviyo list. --dry-run prints the body and skips the POST."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from klaviyo.utils.cli import (
    add_common_flags,
    add_klaviyo_flags,
    configure_logging_from_args,
    format_output,
)
from klaviyo.utils.client import KlaviyoClient, check_errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a Klaviyo list.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--name", required=True, help="List name")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = {"data": {"type": "list", "attributes": {"name": args.name}}}

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("lists", json=body)

    check_errors(result)
    resource = result.get("data") or {}
    print(
        format_output(
            {"id": resource.get("id"), "name": (resource.get("attributes") or {}).get("name")},
            args.output,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Implement `klaviyo/scripts/lists/update.py`.** Complete code:

```python
"""Update a Klaviyo list by id. --dry-run prints the body and skips the PATCH."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from klaviyo.utils.cli import (
    add_common_flags,
    add_klaviyo_flags,
    configure_logging_from_args,
    format_output,
)
from klaviyo.utils.client import KlaviyoClient, check_errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update a Klaviyo list by id.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="List id")
    parser.add_argument("--name", required=True, help="New list name")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = {"data": {"type": "list", "id": args.id, "attributes": {"name": args.name}}}

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.patch(f"lists/{args.id}", json=body)

    check_errors(result)
    resource = result.get("data") or {}
    print(
        format_output(
            {"id": resource.get("id"), "name": (resource.get("attributes") or {}).get("name")},
            args.output,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_lists_create.py tests/klaviyo/scripts/test_lists_update.py -v
uv run ruff check klaviyo/scripts/lists/create.py klaviyo/scripts/lists/update.py tests/klaviyo/scripts/test_lists_create.py tests/klaviyo/scripts/test_lists_update.py
uv run ruff format klaviyo/scripts/lists/create.py klaviyo/scripts/lists/update.py tests/klaviyo/scripts/test_lists_create.py tests/klaviyo/scripts/test_lists_update.py
git add klaviyo/scripts/lists/create.py klaviyo/scripts/lists/update.py tests/klaviyo/scripts/test_lists_create.py tests/klaviyo/scripts/test_lists_update.py
git commit -m "feat(klaviyo): lists/create.py and lists/update.py with --dry-run"
```

---

## Task 12: `lists/delete.py` (gated)

`DELETE /lists/{id}`. `--yes`-gated; `--dry-run` works without `--yes`. Mirrors `webhooks/delete.py` exactly.

**Files:**
- Create: `klaviyo/scripts/lists/delete.py`
- Create: `tests/klaviyo/scripts/test_lists_delete.py`

- [ ] **Step 1: Write failing test.** Write `tests/klaviyo/scripts/test_lists_delete.py`:

```python
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.lists import delete as deletecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.lists.delete.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.lists.delete.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_delete_dry_run_skips_call_without_yes(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(sys, "argv", ["delete.py", "--id", "LST1", "--dry-run"]):
            assert deletecmd.main() == 0
        assert client.delete.call_count == 0
    assert "LST1" in capsys.readouterr().out


def test_delete_without_yes_errors(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(sys, "argv", ["delete.py", "--id", "LST1"]):
            try:
                rc = deletecmd.main()
            except SystemExit as e:
                rc = e.code
        assert rc != 0
        assert client.delete.call_count == 0


def test_delete_with_yes_calls(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.delete.return_value = {}
        with patch.object(sys, "argv", ["delete.py", "--id", "LST1", "--yes"]):
            assert deletecmd.main() == 0
        client.delete.assert_called_once_with("lists/LST1")
    assert "Deleted: LST1" in capsys.readouterr().out
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_lists_delete.py -v
```

- [ ] **Step 3: Implement `klaviyo/scripts/lists/delete.py`.** Complete code:

```python
"""Delete a Klaviyo list by id.

Destructive: requires --yes for live execution. --dry-run prints the intended
deletion and exits 0 without requiring --yes.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from klaviyo.utils.cli import add_common_flags, add_klaviyo_flags, configure_logging_from_args
from klaviyo.utils.client import KlaviyoClient, check_errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Delete a Klaviyo list by id.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="List id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if args.dry_run:
        print(f"Would delete list {args.id}")
        return 0

    if not args.yes:
        parser.error("--yes is required to confirm deletion; aborting")

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.delete(f"lists/{args.id}")

    check_errors(result)
    print(f"Deleted: {args.id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_lists_delete.py -v
uv run ruff check klaviyo/scripts/lists/delete.py tests/klaviyo/scripts/test_lists_delete.py
uv run ruff format klaviyo/scripts/lists/delete.py tests/klaviyo/scripts/test_lists_delete.py
git add klaviyo/scripts/lists/delete.py tests/klaviyo/scripts/test_lists_delete.py
git commit -m "feat(klaviyo): lists/delete.py gated on --yes"
```

---

## Task 13: `lists/add_profiles.py` and `lists/remove_profiles.py`

`POST`/`DELETE /lists/{id}/relationships/profiles` with a JSON:API relationship body (`{"data": [{"type":"profile","id":...}]}`). `add_profiles` has `--dry-run`; `remove_profiles` has `--dry-run` and is `--yes`-gated.

**Files:**
- Create: `klaviyo/scripts/lists/add_profiles.py`
- Create: `klaviyo/scripts/lists/remove_profiles.py`
- Create: `tests/klaviyo/scripts/test_lists_add_profiles.py`
- Create: `tests/klaviyo/scripts/test_lists_remove_profiles.py`

- [ ] **Step 1: Write failing tests.** Write `tests/klaviyo/scripts/test_lists_add_profiles.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.lists import add_profiles as addcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.lists.add_profiles.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.lists.add_profiles.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_add_profiles_dry_run_builds_relationship_body(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["add_profiles.py", "--id", "LST1", "--profile-id", "P1", "--profile-id", "P2", "--dry-run", "--output", "json"],
        ):
            assert addcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    ids = [d["id"] for d in parsed["data"]]
    assert ids == ["P1", "P2"]
    assert parsed["data"][0]["type"] == "profile"


def test_add_profiles_posts_to_relationships(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {}
        with patch.object(
            sys, "argv", ["add_profiles.py", "--id", "LST1", "--profile-id", "P1"]
        ):
            assert addcmd.main() == 0
        args, _ = client.post.call_args
        assert args[0] == "lists/LST1/relationships/profiles"
```

Write `tests/klaviyo/scripts/test_lists_remove_profiles.py`:

```python
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.lists import remove_profiles as rmcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.lists.remove_profiles.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.lists.remove_profiles.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_remove_dry_run_skips_call_without_yes(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["remove_profiles.py", "--id", "LST1", "--profile-id", "P1", "--dry-run"]
        ):
            assert rmcmd.main() == 0
        assert client.delete.call_count == 0


def test_remove_without_yes_errors(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["remove_profiles.py", "--id", "LST1", "--profile-id", "P1"]
        ):
            try:
                rc = rmcmd.main()
            except SystemExit as e:
                rc = e.code
        assert rc != 0
        assert client.delete.call_count == 0


def test_remove_with_yes_calls_delete_with_body(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.delete.return_value = {}
        with patch.object(
            sys, "argv", ["remove_profiles.py", "--id", "LST1", "--profile-id", "P1", "--yes"]
        ):
            assert rmcmd.main() == 0
        args, kwargs = client.delete.call_args
        assert args[0] == "lists/LST1/relationships/profiles"
        body = kwargs["json"]
        assert body["data"][0]["id"] == "P1"
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_lists_add_profiles.py tests/klaviyo/scripts/test_lists_remove_profiles.py -v
```

- [ ] **Step 3: Implement `klaviyo/scripts/lists/add_profiles.py`.** Complete code:

```python
"""Add profiles to a Klaviyo list via the relationships endpoint.

Builds a JSON:API relationship body from one or more --profile-id values.
--dry-run prints the body and skips the POST.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from klaviyo.utils.cli import (
    add_common_flags,
    add_klaviyo_flags,
    configure_logging_from_args,
    format_output,
)
from klaviyo.utils.client import KlaviyoClient, check_errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Add profiles to a Klaviyo list.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="List id")
    parser.add_argument(
        "--profile-id",
        dest="profile_ids",
        action="append",
        required=True,
        help="Profile id to add (repeatable)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = {"data": [{"type": "profile", "id": pid} for pid in args.profile_ids]}

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post(f"lists/{args.id}/relationships/profiles", json=body)

    check_errors(result)
    print(f"Added {len(args.profile_ids)} profile(s) to list {args.id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Implement `klaviyo/scripts/lists/remove_profiles.py`.** Complete code:

```python
"""Remove profiles from a Klaviyo list via the relationships endpoint.

High-stakes: --yes is required for live execution. --dry-run works without
--yes and prints the body without calling the API.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from klaviyo.utils.cli import (
    add_common_flags,
    add_klaviyo_flags,
    configure_logging_from_args,
    format_output,
)
from klaviyo.utils.client import KlaviyoClient, check_errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Remove profiles from a Klaviyo list.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="List id")
    parser.add_argument(
        "--profile-id",
        dest="profile_ids",
        action="append",
        required=True,
        help="Profile id to remove (repeatable)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = {"data": [{"type": "profile", "id": pid} for pid in args.profile_ids]}

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    if not args.yes:
        parser.error("--yes is required to confirm removal; aborting")

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.delete(f"lists/{args.id}/relationships/profiles", json=body)

    check_errors(result)
    print(f"Removed {len(args.profile_ids)} profile(s) from list {args.id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_lists_add_profiles.py tests/klaviyo/scripts/test_lists_remove_profiles.py -v
uv run ruff check klaviyo/scripts/lists/add_profiles.py klaviyo/scripts/lists/remove_profiles.py tests/klaviyo/scripts/test_lists_add_profiles.py tests/klaviyo/scripts/test_lists_remove_profiles.py
uv run ruff format klaviyo/scripts/lists/add_profiles.py klaviyo/scripts/lists/remove_profiles.py tests/klaviyo/scripts/test_lists_add_profiles.py tests/klaviyo/scripts/test_lists_remove_profiles.py
git add klaviyo/scripts/lists/add_profiles.py klaviyo/scripts/lists/remove_profiles.py tests/klaviyo/scripts/test_lists_add_profiles.py tests/klaviyo/scripts/test_lists_remove_profiles.py
git commit -m "feat(klaviyo): lists/add_profiles.py and lists/remove_profiles.py (gated)"
```

---

## Task 14: `segments/list.py` and `segments/get.py`

Read-only (segment create/update deferred — spec §2). Same shape as `lists/list.py`/`lists/get.py`.

**Files:**
- Create: `klaviyo/scripts/segments/__init__.py`
- Create: `klaviyo/scripts/segments/list.py`
- Create: `klaviyo/scripts/segments/get.py`
- Create: `tests/klaviyo/scripts/test_segments_list.py`
- Create: `tests/klaviyo/scripts/test_segments_get.py`

- [ ] **Step 1: Create the segments package marker.**

```bash
mkdir -p klaviyo/scripts/segments
touch klaviyo/scripts/segments/__init__.py
```

- [ ] **Step 2: Write failing tests.** Write `tests/klaviyo/scripts/test_segments_list.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.segments import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.segments.list.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.segments.list.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_segments_list_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [{"id": "SEG1", "type": "segment", "attributes": {"name": "Engaged"}}]
        )
        with patch.object(sys, "argv", ["list.py", "--output", "json"]):
            assert listcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "SEG1"
    assert parsed[0]["name"] == "Engaged"
```

Write `tests/klaviyo/scripts/test_segments_get.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.segments import get as getcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.segments.get.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.segments.get.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_get_segment_by_id(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "data": {"id": "SEG1", "type": "segment", "attributes": {"name": "Engaged"}}
        }
        with patch.object(sys, "argv", ["get.py", "--id", "SEG1", "--output", "json"]):
            assert getcmd.main() == 0
        client.get.assert_called_once_with("segments/SEG1")
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "SEG1"
    assert parsed["name"] == "Engaged"


def test_get_segment_with_members(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "data": {"id": "SEG1", "type": "segment", "attributes": {"name": "Engaged"}}
        }
        client.paginate.return_value = iter(
            [{"id": "01H", "type": "profile", "attributes": {"email": "a@b.com"}}]
        )
        with patch.object(
            sys, "argv", ["get.py", "--id", "SEG1", "--with-members", "--output", "json"]
        ):
            assert getcmd.main() == 0
        client.paginate.assert_called_once()
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["members"][0]["email"] == "a@b.com"
```

- [ ] **Step 3: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_segments_list.py tests/klaviyo/scripts/test_segments_get.py -v
```

- [ ] **Step 4: Implement `klaviyo/scripts/segments/list.py`.** Complete code:

```python
"""List Klaviyo segments (read-only; segment authoring is deferred — spec §2)."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from klaviyo.utils.cli import (
    add_common_flags,
    add_klaviyo_flags,
    configure_logging_from_args,
    format_output,
)
from klaviyo.utils.client import KlaviyoClient


def _flatten(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "name": attrs.get("name"),
        "created": attrs.get("created"),
        "updated": attrs.get("updated"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Klaviyo segments.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        rows = [_flatten(r) for r in client.paginate("segments", limit=args.limit)]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Implement `klaviyo/scripts/segments/get.py`.** Complete code:

```python
"""Get a Klaviyo segment by id, optionally with its member profiles.

--with-members appends a paginated profile listing (capped by --limit) under a
``members`` key. Read-only; segment authoring is deferred (spec §2).
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from klaviyo.utils.cli import (
    add_common_flags,
    add_klaviyo_flags,
    configure_logging_from_args,
    format_output,
)
from klaviyo.utils.client import KlaviyoClient, check_errors


def _flatten_segment(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "name": attrs.get("name"),
        "created": attrs.get("created"),
        "updated": attrs.get("updated"),
    }


def _flatten_profile(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "email": attrs.get("email"),
        "first_name": attrs.get("first_name"),
        "last_name": attrs.get("last_name"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get a Klaviyo segment by id.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Segment id")
    parser.add_argument(
        "--with-members",
        dest="with_members",
        action="store_true",
        help="Also list member profiles (capped by --limit)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        body = client.get(f"segments/{args.id}")
        check_errors(body)
        out = _flatten_segment(body.get("data") or {})
        if args.with_members:
            out["members"] = [
                _flatten_profile(r)
                for r in client.paginate(f"segments/{args.id}/profiles", limit=args.limit)
            ]

    print(format_output(out, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_segments_list.py tests/klaviyo/scripts/test_segments_get.py -v
uv run ruff check klaviyo/scripts/segments/ tests/klaviyo/scripts/test_segments_list.py tests/klaviyo/scripts/test_segments_get.py
uv run ruff format klaviyo/scripts/segments/ tests/klaviyo/scripts/test_segments_list.py tests/klaviyo/scripts/test_segments_get.py
git add klaviyo/scripts/segments/__init__.py klaviyo/scripts/segments/list.py klaviyo/scripts/segments/get.py tests/klaviyo/scripts/test_segments_list.py tests/klaviyo/scripts/test_segments_get.py
git commit -m "feat(klaviyo): segments/list.py and segments/get.py (read-only)"
```

---

## Task 15: Skills — `klaviyo-profiles` and `klaviyo-lists`

**Files:**
- Create: `skills/klaviyo-profiles/SKILL.md`
- Create: `skills/klaviyo-lists/SKILL.md`

Mirror the `skills/shopify-webhooks/SKILL.md` front-matter shape: a `name:` line and a single-paragraph `description:` packed with trigger phrases and the per-script flag posture (which scripts honor `--dry-run`, which require `--yes`), then a body covering when to use, each script, and a "defer to direct API use" note for unsupported ops (e.g. segment authoring).

- [ ] **Step 1: Write `skills/klaviyo-profiles/SKILL.md`.** Covers `profiles/{list,get,create,update,subscribe,unsubscribe}` and `segments/{list,get}` (segments folded in here per spec §10). Front-matter `description` must name triggers: "list profiles", "find profile by email", "create a profile", "update a profile", "subscribe a profile", "unsubscribe a profile", "list segments", "show segment members". Note `--dry-run` on create/update/subscribe/unsubscribe and `--yes` on unsubscribe; note segment authoring is deferred to direct API use.

- [ ] **Step 2: Write `skills/klaviyo-lists/SKILL.md`.** Covers `lists/{list,get,create,update,delete,add_profiles,remove_profiles}`. Triggers: "list my Klaviyo lists", "create a list", "rename a list", "delete a list", "add profiles to a list", "remove profiles from a list". Note `--dry-run` on all mutations and `--yes` on `delete`/`remove_profiles`.

- [ ] **Step 3: Commit.**

```bash
git add skills/klaviyo-profiles/SKILL.md skills/klaviyo-lists/SKILL.md
git commit -m "docs(klaviyo): klaviyo-profiles and klaviyo-lists skills"
```

---

## Task 16: Full sweep, CHANGELOG, smoke

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Full suite + ruff (with the klaviyo extra installed).**

```bash
uv sync --extra dev --extra shopify --extra webhooks --extra klaviyo
uv run pytest tests/ --ignore=tests/shopify/test_whoami_integration.py -v
uv run ruff check .
uv run ruff format --check .
```
Expected: all green; the new `tests/klaviyo/` suite is collected and passes; existing Shopify tests unaffected.

- [ ] **Step 2: Smoke each script's `--help` and a representative `--dry-run`.**

```bash
uv run klaviyo/scripts/profiles/list.py --help
uv run klaviyo/scripts/profiles/create.py --email a@b.com --dry-run --output json
uv run klaviyo/scripts/lists/delete.py --id LST1 --dry-run
uv run klaviyo/scripts/profiles/unsubscribe.py --email a@b.com --list-id LST1 --dry-run
```
Expected: help text prints; `--dry-run` prints the JSON:API body / intent and exits 0 without needing a real API key or `--yes`.

- [ ] **Step 3: Update `CHANGELOG.md`.** Add an entry under a new version heading (bump the `0.5.1` patch line; e.g. `## [0.6.0] — 2026-05-29`) noting: Klaviyo domain foundation (`KlaviyoClient`, CLI helpers, `klaviyo` extra populated, config + CI wiring) and the audience cluster scripts (profiles, lists, segments) with `--dry-run`/`--yes` posture.

- [ ] **Step 4: Commit.**

```bash
git add CHANGELOG.md
git commit -m "docs(klaviyo): CHANGELOG for Klaviyo foundation + audience (K1)"
```

---

## Definition of Done

(Scoped to K1, per spec §12.)

- [ ] `uv sync --extra klaviyo` installs and every `klaviyo/scripts/{profiles,lists,segments}/*` script runs (`--help` works).
- [ ] `KlaviyoClient` unit-tested: auth header (`Klaviyo-API-Key`), `revision` header (config value, `--revision` override, `_DEFAULT_REVISION` fallback), `paginate` follows `links.next` and respects `--limit`, `check_errors` raises `KlaviyoAPIError` on JSON:API `errors[]`, `204` delete returns `{}`.
- [ ] Audience CRUD per spec §5 K1: `profiles/{list,get,create,update,subscribe,unsubscribe}`, `lists/{list,get,create,update,delete,add_profiles,remove_profiles}`, `segments/{list,get}`.
- [ ] `--dry-run` on every mutation prints the JSON:API body and skips the call; `--yes` gates `profiles/unsubscribe`, `lists/delete`, `lists/remove_profiles` (errors before any network call when missing in live mode).
- [ ] Per-script unit tests green, mocking `KlaviyoClient` (no live calls); integration tests, if added, gated by `KLAVIYO_INTEGRATION_TESTS=1` and skipped by default.
- [ ] `klaviyo` extra populated in `pyproject.toml`; `domains.klaviyo` wired as `{enabled, api_version}` in `store-config.example.yaml`; CI installs `--extra klaviyo`.
- [ ] `klaviyo-profiles` and `klaviyo-lists` skills present and cover their clusters.
- [ ] Full `uv run pytest tests/` green; `ruff check .` and `ruff format --check .` clean. CHANGELOG bumped.
