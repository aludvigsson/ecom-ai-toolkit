# Plan M1: Meta Ads Foundation + Reads + Insights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Meta Ads domain foundation (`MetaClient`, CLI helpers, packaging/config/CI wiring) plus the full structure-read cluster and insights query — accounts, campaigns, ad sets, ads, creatives, and `insights/query` — so a Meta (Facebook/Instagram) Ads account can be inspected and reported on from `uv run meta_ads/scripts/<cluster>/<op>.py`.

**Architecture:** A new `meta_ads/utils/client.py` puts a thin `MetaClient` over `core.http.HttpClient` (Graph API over httpx; `Authorization: Bearer <token>` auth; version segment from `domains.meta_ads.api_version`; `act_<id>` normalization; offset/cursor pagination via `paging.next`; `check_error` raising `MetaAPIError` carrying `code`/`error_subcode`/`fbtrace_id`). `meta_ads/utils/cli.py` near-copies `klaviyo/utils/cli.py` and adds `add_meta_flags` for `--api-version`/`--yes`. Read scripts flatten Graph nodes into flat rows for table output and pass a comma-joined `fields` param; `insights/query` adds `--level`/`--date-preset`|`--time-range`/`--breakdowns`/`--fields`.

**Tech Stack:** `httpx>=0.27`, `pyyaml>=6`, `pydantic>=2.7` (the existing base deps, now populated for the `meta-ads` extra). Tests use `pytest` with `monkeypatch`/`unittest.mock.patch`. No vendor SDK (`facebook-business`), no MCP.

**Spec reference:** `docs/superpowers/specs/2026-05-29-meta-ads-domain-design.md` §3 (architecture — `client.py` §3.1, `cli.py` §3.2), §4 (conventions), §5 M1 (structure-read + insights script inventory), §6 (data flow), §7 (error handling), §9 (config & secrets), §11 (implementation split — Plan M1), §12 (definition of done, scoped here to M1).

**Depends on:** v1 foundation (`core/http.py`, `core/config.py` `DomainConfig.api_version`, `core/secrets.require_secret`). The reserved `meta-ads` extra and `META_ACCESS_TOKEN`/`META_BUSINESS_ID` env entries already exist. No `core/` changes. The Klaviyo domain (`klaviyo/utils/{client,cli}.py`, `klaviyo/scripts/profiles/*`) is the most recent reference for a third-party API domain; Shopify is the conventions baseline.

> **Scope note — writes deferred:** This plan ships only reads + insights. No `create`/`update`/`pause`/`activate`/`delete` scripts (those are Plan M2) and no audiences (Plan M3). `MetaClient.post`/`delete` are implemented now because the client is the shared foundation M2/M3 depend on, but no M1 script calls them. The safe-default-`PAUSED` rule and `--yes` gating land with the write scripts in M2; `add_meta_flags` registers `--yes` now so the flag surface is stable across the domain.

---

## File Structure

| Path | Responsibility |
|---|---|
| `pyproject.toml` | Populate `meta-ads` extra with base deps (modify) |
| `store-config.example.yaml` | `domains.meta_ads` → add `api_version` (modify) |
| `.github/workflows/ci.yml` | Add `--extra meta-ads` to sync step (modify) |
| `meta_ads/__init__.py` | empty package marker |
| `meta_ads/utils/__init__.py` | empty package marker |
| `meta_ads/utils/client.py` | `MetaClient`, `MetaAPIError`, `account_path`, `check_error` |
| `meta_ads/utils/cli.py` | `add_common_flags`, `add_meta_flags`, `configure_logging_from_args`, `format_output` |
| `meta_ads/scripts/__init__.py` | empty |
| `meta_ads/scripts/accounts/__init__.py` | empty |
| `meta_ads/scripts/accounts/list.py` | `GET /<business_id>/owned_ad_accounts` (or `/me/adaccounts`) |
| `meta_ads/scripts/accounts/get.py` | `GET /act_<id>` — field selection |
| `meta_ads/scripts/campaigns/__init__.py` | empty |
| `meta_ads/scripts/campaigns/list.py` | `GET /act_<id>/campaigns` — `--account-id`, `--status` |
| `meta_ads/scripts/campaigns/get.py` | `GET /<campaign_id>` |
| `meta_ads/scripts/adsets/__init__.py` | empty |
| `meta_ads/scripts/adsets/list.py` | `GET /act_<id>/adsets` or `/<campaign_id>/adsets` |
| `meta_ads/scripts/adsets/get.py` | `GET /<adset_id>` |
| `meta_ads/scripts/ads/__init__.py` | empty |
| `meta_ads/scripts/ads/list.py` | `GET /act_<id>/ads` or `/<adset_id>/ads` |
| `meta_ads/scripts/ads/get.py` | `GET /<ad_id>` |
| `meta_ads/scripts/creatives/__init__.py` | empty |
| `meta_ads/scripts/creatives/list.py` | `GET /act_<id>/adcreatives` |
| `meta_ads/scripts/creatives/get.py` | `GET /<creative_id>` |
| `meta_ads/scripts/insights/__init__.py` | empty |
| `meta_ads/scripts/insights/query.py` | `GET /<object_id>/insights` — level/date/breakdowns/fields |
| `tests/meta_ads/__init__.py` | empty |
| `tests/meta_ads/utils/__init__.py` | empty |
| `tests/meta_ads/utils/test_client.py` | `MetaClient` unit tests (auth, version, `act_` norm, paging, check_error) |
| `tests/meta_ads/utils/test_cli.py` | CLI helper tests |
| `tests/meta_ads/scripts/__init__.py` | empty |
| `tests/meta_ads/scripts/test_accounts_*.py` | accounts script tests |
| `tests/meta_ads/scripts/test_campaigns_*.py` | campaigns script tests |
| `tests/meta_ads/scripts/test_adsets_*.py` | adsets script tests |
| `tests/meta_ads/scripts/test_ads_*.py` | ads script tests |
| `tests/meta_ads/scripts/test_creatives_*.py` | creatives script tests |
| `tests/meta_ads/scripts/test_insights_query.py` | insights query tests |
| `skills/meta-ads-structure/SKILL.md` | structure reads cluster skill (read sections) |
| `skills/meta-ads-insights/SKILL.md` | insights cluster skill |

---

## Task 1: Packaging, config, and CI wiring

**Files:**
- Modify: `pyproject.toml`
- Modify: `store-config.example.yaml`
- Modify: `.github/workflows/ci.yml`
- Create: `meta_ads/__init__.py`
- Create: `meta_ads/utils/__init__.py`
- Create: `meta_ads/scripts/__init__.py`

- [ ] **Step 1: Populate the `meta-ads` extra.** Edit `pyproject.toml`, replacing the empty `meta-ads` extra with the same base deps the `shopify`/`klaviyo` extras use:

```toml
meta-ads        = ["httpx>=0.27", "pyyaml>=6", "pydantic>=2.7"]
```

- [ ] **Step 2: Verify it installs.**

```bash
uv sync --extra dev --extra meta-ads
```
Expected: resolves and installs with no error (httpx/pyyaml/pydantic already present from `shopify`/`klaviyo`).

- [ ] **Step 3: Wire `domains.meta_ads` in the example config.** Edit `store-config.example.yaml`, replacing the `meta_ads` line so it carries the Graph API version in `api_version` (the current line lacks it):

```yaml
  meta_ads:       { enabled: false, api_version: "v21.0" }
```

- [ ] **Step 4: Add the `meta-ads` extra to CI.** Edit `.github/workflows/ci.yml`, changing the `Sync deps` step:

```yaml
      - name: Sync deps
        run: uv sync --extra dev --extra shopify --extra webhooks --extra klaviyo --extra meta-ads
```

- [ ] **Step 5: Create the empty package markers.**

```bash
mkdir -p meta_ads/utils meta_ads/scripts
touch meta_ads/__init__.py meta_ads/utils/__init__.py meta_ads/scripts/__init__.py
```

- [ ] **Step 6: Commit.**

```bash
git add pyproject.toml store-config.example.yaml .github/workflows/ci.yml meta_ads/__init__.py meta_ads/utils/__init__.py meta_ads/scripts/__init__.py
git commit -m "feat(meta-ads): populate meta-ads extra, wire config + CI, package skeleton"
```

---

## Task 2: `meta_ads/utils/client.py` — MetaClient

This is the shared foundation every M-plan depends on. It mirrors `KlaviyoClient` in shape (reads its secret at construction, thin verb wrappers over `core.http.HttpClient`, context manager) but speaks the **Graph API**: a versioned base URL, Bearer auth, `act_<id>` normalization, `paging.next`-following pagination, and a `check_error` that surfaces the Graph `error{message,code,error_subcode,fbtrace_id}` object.

**Files:**
- Create: `meta_ads/utils/client.py`
- Create: `tests/meta_ads/__init__.py`
- Create: `tests/meta_ads/utils/__init__.py`
- Create: `tests/meta_ads/utils/test_client.py`

- [ ] **Step 1: Create the test package markers.**

```bash
mkdir -p tests/meta_ads/utils
touch tests/meta_ads/__init__.py tests/meta_ads/utils/__init__.py
```

- [ ] **Step 2: Write failing tests.** Write `tests/meta_ads/utils/test_client.py`. These mock the underlying `HttpClient` either by patching `meta_ads.utils.client.HttpClient` (to capture construction kwargs) or by assigning `client._http` after construction (so no real HTTP happens; construction needs only the secret + config).

```python
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from meta_ads.utils.client import (
    MetaAPIError,
    MetaClient,
    account_path,
    check_error,
)


def _config(api_version="v21.0"):
    domain = SimpleNamespace(enabled=True, api_version=api_version)
    store = SimpleNamespace(shopify_domain="example-store.myshopify.com")
    return SimpleNamespace(store=store, domains={"meta_ads": domain})


def _response(json_body, status_code=200):
    resp = MagicMock()
    resp.json.return_value = json_body
    resp.status_code = status_code
    resp.content = b"{}"
    return resp


def test_account_path_normalizes_with_and_without_prefix():
    assert account_path("123") == "act_123"
    assert account_path("act_123") == "act_123"
    assert account_path(123) == "act_123"


def test_client_sets_bearer_auth_and_versioned_base_url(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    captured = {}

    def fake_http(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    monkeypatch.setattr("meta_ads.utils.client.HttpClient", fake_http)
    MetaClient(config=_config())
    assert captured["base_url"] == "https://graph.facebook.com/v21.0/"
    headers = captured["default_headers"]
    assert headers["Authorization"] == "Bearer EAAexampletoken"


def test_client_api_version_override_wins(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    captured = {}
    monkeypatch.setattr(
        "meta_ads.utils.client.HttpClient",
        lambda **kw: captured.update(kw) or MagicMock(),
    )
    MetaClient(config=_config(api_version=None), api_version="v19.0")
    assert captured["base_url"] == "https://graph.facebook.com/v19.0/"


def test_client_api_version_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    captured = {}
    monkeypatch.setattr(
        "meta_ads.utils.client.HttpClient",
        lambda **kw: captured.update(kw) or MagicMock(),
    )
    from meta_ads.utils.client import _DEFAULT_VERSION

    MetaClient(config=_config(api_version=None))
    assert captured["base_url"] == f"https://graph.facebook.com/{_DEFAULT_VERSION}/"


def test_get_returns_parsed_body(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    client = MetaClient(config=_config())
    client._http = MagicMock()
    client._http.get.return_value = _response({"data": [{"id": "c1"}]})
    body = client.get("act_123/campaigns", params={"fields": "id,name"})
    assert body == {"data": [{"id": "c1"}]}
    client._http.get.assert_called_once()


def test_post_returns_parsed_body(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    client = MetaClient(config=_config())
    client._http = MagicMock()
    client._http.post.return_value = _response({"id": "c9"})
    assert client.post("act_123/campaigns", data={"name": "X"}) == {"id": "c9"}
    _, kwargs = client._http.post.call_args
    assert kwargs["data"] == {"name": "X"}


def test_delete_empty_body_returns_empty(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    client = MetaClient(config=_config())
    resp = MagicMock()
    resp.status_code = 200
    resp.content = b""
    client._http = MagicMock()
    client._http.delete.return_value = resp
    assert client.delete("c9") == {}


def test_paginate_follows_paging_next(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    client = MetaClient(config=_config())
    page1 = _response(
        {
            "data": [{"id": "a"}, {"id": "b"}],
            "paging": {
                "next": "https://graph.facebook.com/v21.0/act_123/campaigns?after=NEXT"
            },
        }
    )
    page2 = _response({"data": [{"id": "c"}], "paging": {}})
    client._http = MagicMock()
    client._http.get.side_effect = [page1, page2]
    items = list(client.paginate("act_123/campaigns"))
    assert [i["id"] for i in items] == ["a", "b", "c"]
    assert client._http.get.call_count == 2


def test_paginate_respects_limit(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    client = MetaClient(config=_config())
    page = _response(
        {
            "data": [{"id": str(n)} for n in range(50)],
            "paging": {
                "next": "https://graph.facebook.com/v21.0/act_123/campaigns?after=NEXT"
            },
        }
    )
    client._http = MagicMock()
    client._http.get.return_value = page
    items = list(client.paginate("act_123/campaigns", limit=10))
    assert len(items) == 10


def test_check_error_raises_with_all_fields():
    body = {
        "error": {
            "message": "Invalid parameter",
            "code": 100,
            "error_subcode": 1487056,
            "fbtrace_id": "AbC123xyz",
        }
    }
    with pytest.raises(MetaAPIError) as exc:
        check_error(body)
    msg = str(exc.value)
    assert "Invalid parameter" in msg
    assert "100" in msg
    assert "1487056" in msg
    assert "AbC123xyz" in msg
    assert exc.value.code == 100
    assert exc.value.subcode == 1487056
    assert exc.value.fbtrace_id == "AbC123xyz"


def test_check_error_token_code_names_env_var():
    body = {"error": {"message": "expired", "code": 190, "fbtrace_id": "Z"}}
    with pytest.raises(MetaAPIError) as exc:
        check_error(body)
    assert "META_ACCESS_TOKEN" in str(exc.value)


def test_check_error_noop_on_clean_body():
    check_error({"data": [{"id": "c1"}]})  # no raise
```

- [ ] **Step 3: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/utils/test_client.py -v
```
Expected: collection/import error — `ModuleNotFoundError: No module named 'meta_ads.utils.client'`.

- [ ] **Step 4: Implement `meta_ads/utils/client.py`.** Complete code:

```python
"""Meta (Facebook/Instagram) Marketing Graph API client on core.http.HttpClient.

Mirrors klaviyo.utils.client.KlaviyoClient in shape (reads its secret at
construction, thin verb wrappers over core.http.HttpClient which retries
429/5xx, context manager) but speaks the Graph API: a versioned base URL,
``Authorization: Bearer <token>`` auth, ``act_<id>`` account-id normalization,
``paging.next``-following pagination, and ``check_error`` surfacing the Graph
``error{message,code,error_subcode,fbtrace_id}`` object.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from core.config import StoreConfig
from core.http import HttpClient
from core.logging import get_logger
from core.secrets import require_secret

_log = get_logger("ecom.meta_ads.client")

# Known-good Graph API version used when domains.meta_ads.api_version is unset.
# Override per-invocation with --api-version (see meta_ads.utils.cli.add_meta_flags).
_DEFAULT_VERSION = "v21.0"

# Graph error codes that mean the access token is bad/expired.
_TOKEN_ERROR_CODES = {102, 190}


class MetaAPIError(RuntimeError):
    """Raised when a Graph response carries a top-level ``error`` object.

    Surfaces ``message``, ``code``, ``error_subcode``, and ``fbtrace_id`` (the
    last is essential when escalating to Meta support). Token errors (code
    102/190) additionally name the ``META_ACCESS_TOKEN`` env var.
    """

    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        subcode: int | None = None,
        fbtrace_id: str | None = None,
        body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.subcode = subcode
        self.fbtrace_id = fbtrace_id
        self.body = body


def account_path(account_id: str | int) -> str:
    """Normalize an ad-account id to the Graph ``act_<id>`` node form.

    Accepts a bare id (``"123"``/``123``) or an already-prefixed ``"act_123"``.
    """
    text = str(account_id)
    return text if text.startswith("act_") else f"act_{text}"


def check_error(body: dict[str, Any] | None) -> None:
    """Raise MetaAPIError if ``body['error']`` is present.

    Free function for direct import:
        from meta_ads.utils.client import check_error
    """
    if not body:
        return
    error = body.get("error")
    if not error:
        return
    message = error.get("message") or "?"
    code = error.get("code")
    subcode = error.get("error_subcode")
    fbtrace_id = error.get("fbtrace_id")
    parts = [message]
    if code is not None:
        parts.append(f"code={code}")
    if subcode is not None:
        parts.append(f"subcode={subcode}")
    if fbtrace_id:
        parts.append(f"fbtrace_id={fbtrace_id}")
    if code in _TOKEN_ERROR_CODES:
        parts.append("(check META_ACCESS_TOKEN)")
    raise MetaAPIError(
        " ".join(parts),
        code=code,
        subcode=subcode,
        fbtrace_id=fbtrace_id,
        body=body,
    )


class MetaClient:
    """Meta Marketing Graph API client.

    Reads META_ACCESS_TOKEN from the environment at construction time. The Graph
    API version segment of the base URL comes from
    config.domains['meta_ads'].api_version, falling back to _DEFAULT_VERSION,
    overridable via the ``api_version`` argument.
    """

    def __init__(self, config: StoreConfig, *, api_version: str | None = None) -> None:
        self._config = config
        token = require_secret("META_ACCESS_TOKEN")
        domain = config.domains.get("meta_ads")
        configured = domain.api_version if domain else None
        self._version = api_version or configured or _DEFAULT_VERSION
        self._http = HttpClient(
            base_url=f"https://graph.facebook.com/{self._version}/",
            default_headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )

    @property
    def api_version(self) -> str:
        return self._version

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._http.get(path, params=params)
        return response.json()

    def post(self, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """POST form-encoded data (Graph creates/updates are form POSTs)."""
        response = self._http.post(path, data=data)
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def delete(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._http.delete(path, params=params)
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
        """Yield ``data[]`` items across pages by following ``paging.next``.

        The Graph API returns a fully-qualified ``paging.next`` URL (carrying the
        cursor), so subsequent requests pass it through unchanged. When ``limit``
        is set, stops after yielding that many items (logs a truncation notice).
        """
        next_url: str | None = path
        first = True
        yielded = 0
        while next_url:
            body = self.get(next_url, params=params if first else None)
            first = False
            check_error(body)
            for item in body.get("data") or []:
                if limit is not None and yielded >= limit:
                    _log.info("paginate truncated at limit=%d for %s", limit, path)
                    return
                yield item
                yielded += 1
            next_url = (body.get("paging") or {}).get("next")

    def __enter__(self) -> MetaClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()
```

- [ ] **Step 5: Run, confirm pass.**

```bash
uv run pytest tests/meta_ads/utils/test_client.py -v
```
Expected: all tests pass.

- [ ] **Step 6: Ruff + commit.**

```bash
uv run ruff check meta_ads/utils/client.py tests/meta_ads/utils/test_client.py
uv run ruff format meta_ads/utils/client.py tests/meta_ads/utils/test_client.py
git add meta_ads/utils/client.py tests/meta_ads/__init__.py tests/meta_ads/utils/
git commit -m "feat(meta-ads): MetaClient (Bearer auth, versioned base, act_ norm, paging, check_error)"
```

---

## Task 3: `meta_ads/utils/cli.py` — CLI helpers

Near-copy of `klaviyo/utils/cli.py` plus `add_meta_flags` registering `--api-version` and `--yes`.

**Files:**
- Create: `meta_ads/utils/cli.py`
- Create: `tests/meta_ads/utils/test_cli.py`

- [ ] **Step 1: Write failing tests.** Write `tests/meta_ads/utils/test_cli.py`:

```python
import argparse
import json

from meta_ads.utils import cli


def _parsed(argv):
    parser = argparse.ArgumentParser()
    cli.add_common_flags(parser)
    cli.add_meta_flags(parser)
    return parser.parse_args(argv)


def test_common_flag_defaults():
    args = _parsed([])
    assert args.output == "table"
    assert args.limit == 50
    assert args.config == "store-config.yaml"
    assert args.dry_run is False
    assert args.verbose is False


def test_meta_flags_api_version_and_yes():
    args = _parsed(["--api-version", "v19.0", "--yes"])
    assert args.api_version == "v19.0"
    assert args.yes is True


def test_meta_flag_defaults():
    args = _parsed([])
    assert args.api_version is None
    assert args.yes is False


def test_format_output_json():
    out = cli.format_output([{"id": "c1", "name": "Camp"}], "json")
    assert json.loads(out) == [{"id": "c1", "name": "Camp"}]


def test_format_output_table_renders_rows():
    out = cli.format_output([{"id": "c1", "name": "Camp"}], "table")
    assert "id" in out and "name" in out and "c1" in out


def test_format_output_empty_table():
    assert cli.format_output([], "table") == "(no rows)"
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/utils/test_cli.py -v
```
Expected: `ModuleNotFoundError: No module named 'meta_ads.utils.cli'`.

- [ ] **Step 3: Implement `meta_ads/utils/cli.py`.** Complete code:

```python
"""Shared argparse + output helpers for meta_ads/scripts/.

A near-copy of klaviyo/utils/cli.py (duplicated rather than imported to avoid
coupling domains; promoting to core/cli.py is a deferred follow-up — spec
§3.2). Adds add_meta_flags for the domain-specific --api-version/--yes flags.
"""

from __future__ import annotations

import argparse
import json
import logging
from typing import Any


def add_common_flags(parser: argparse.ArgumentParser) -> None:
    """Register the conventions every meta_ads/scripts/* script supports."""
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip writes; print the Graph request and exit 0",
    )
    parser.add_argument(
        "--output",
        choices=("table", "json", "markdown"),
        default="table",
    )
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--config", default="store-config.yaml")
    parser.add_argument("--verbose", action="store_true")


def add_meta_flags(parser: argparse.ArgumentParser) -> None:
    """Register Meta-specific flags.

    --api-version overrides the Graph API version the client otherwise reads
    from domains.meta_ads.api_version. --yes confirms high-stakes operations
    (gated writes land in Plan M2/M3; the flag surface is registered now so it
    is stable across the domain).
    """
    parser.add_argument(
        "--api-version",
        dest="api_version",
        default=None,
        help="Override the Graph API version (default: config api_version)",
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
uv run pytest tests/meta_ads/utils/test_cli.py -v
```
Expected: all tests pass.

- [ ] **Step 5: Ruff + commit.**

```bash
uv run ruff check meta_ads/utils/cli.py tests/meta_ads/utils/test_cli.py
uv run ruff format meta_ads/utils/cli.py tests/meta_ads/utils/test_cli.py
git add meta_ads/utils/cli.py tests/meta_ads/utils/test_cli.py
git commit -m "feat(meta-ads): cli helpers (add_common_flags, add_meta_flags, format_output)"
```

---

## Task 4: `accounts/list.py` (reference read script)

First script of the accounts resource and the template for every list-read script: resolve the parent node (`--business-id` or config `META_BUSINESS_ID`, else `/me/adaccounts`), build a comma-joined `fields` param, flatten Graph nodes into flat rows, page via `paginate` capped by `--limit`.

**Files:**
- Create: `meta_ads/scripts/accounts/__init__.py`
- Create: `meta_ads/scripts/accounts/list.py`
- Create: `tests/meta_ads/scripts/__init__.py`
- Create: `tests/meta_ads/scripts/test_accounts_list.py`

- [ ] **Step 1: Create test/script package markers.**

```bash
mkdir -p meta_ads/scripts/accounts tests/meta_ads/scripts
touch meta_ads/scripts/accounts/__init__.py tests/meta_ads/scripts/__init__.py
```

- [ ] **Step 2: Write failing test.** Write `tests/meta_ads/scripts/test_accounts_list.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from meta_ads.scripts.accounts import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.accounts.list.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.accounts.list.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_accounts_list_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [
                {
                    "id": "act_123",
                    "account_id": "123",
                    "name": "Main Ad Account",
                    "account_status": 1,
                    "currency": "USD",
                }
            ]
        )
        with patch.object(
            sys, "argv", ["list.py", "--business-id", "999", "--output", "json"]
        ):
            assert listcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "act_123"
    assert parsed[0]["name"] == "Main Ad Account"
    assert parsed[0]["currency"] == "USD"


def test_accounts_list_uses_business_node_and_fields(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py", "--business-id", "999"]):
            assert listcmd.main() == 0
        args, kwargs = client.paginate.call_args
        assert args[0] == "999/owned_ad_accounts"
        params = kwargs.get("params") or args[1]
        assert "name" in params["fields"]
        assert kwargs["limit"] == 50


def test_accounts_list_defaults_to_me_node(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    # skip .env.local loading so META_BUSINESS_ID is genuinely absent
    monkeypatch.setattr("core.secrets._env_loaded", True)
    monkeypatch.delenv("META_BUSINESS_ID", raising=False)
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py"]):
            assert listcmd.main() == 0
        args, _ = client.paginate.call_args
        assert args[0] == "me/adaccounts"


def test_accounts_list_uses_business_id_secret(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    monkeypatch.setattr("core.secrets._env_loaded", True)
    monkeypatch.setenv("META_BUSINESS_ID", "555")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py"]):
            assert listcmd.main() == 0
        args, _ = client.paginate.call_args
        assert args[0] == "555/owned_ad_accounts"
```

- [ ] **Step 3: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_accounts_list.py -v
```
Expected: `ModuleNotFoundError: No module named 'meta_ads.scripts.accounts.list'`.

- [ ] **Step 4: Implement `meta_ads/scripts/accounts/list.py`.** Complete code:

```python
"""List the ad accounts owned by a business (or accessible to the token).

Parent node resolution: --business-id, else the ``META_BUSINESS_ID`` secret,
else ``me/adaccounts``. Flattens Graph ad account nodes into flat rows and
honors --limit via cursor pagination.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from core.secrets import get_secret
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient

_FIELDS = "id,account_id,name,account_status,currency,timezone_name,amount_spent"


def _flatten(node: dict) -> dict:
    return {
        "id": node.get("id"),
        "account_id": node.get("account_id"),
        "name": node.get("name"),
        "account_status": node.get("account_status"),
        "currency": node.get("currency"),
        "timezone_name": node.get("timezone_name"),
        "amount_spent": node.get("amount_spent"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Meta ad accounts.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument(
        "--business-id",
        dest="business_id",
        help="Business id whose owned_ad_accounts to list (default: config or /me)",
    )
    parser.add_argument(
        "--fields",
        default=_FIELDS,
        help="Comma-separated Graph fields to request",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    business_id = args.business_id or get_secret("META_BUSINESS_ID")
    path = f"{business_id}/owned_ad_accounts" if business_id else "me/adaccounts"
    params = {"fields": args.fields}

    with MetaClient(config=cfg, api_version=args.api_version) as client:
        rows = [_flatten(n) for n in client.paginate(path, params=params, limit=args.limit)]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run, confirm pass.**

```bash
uv run pytest tests/meta_ads/scripts/test_accounts_list.py -v
```
Expected: all tests pass.

- [ ] **Step 6: Ruff + commit.**

```bash
uv run ruff check meta_ads/scripts/accounts/list.py tests/meta_ads/scripts/test_accounts_list.py
uv run ruff format meta_ads/scripts/accounts/list.py tests/meta_ads/scripts/test_accounts_list.py
git add meta_ads/scripts/accounts/__init__.py meta_ads/scripts/accounts/list.py tests/meta_ads/scripts/__init__.py tests/meta_ads/scripts/test_accounts_list.py
git commit -m "feat(meta-ads): accounts/list.py with business-node resolution + field selection"
```

---

## Task 5: `accounts/get.py` (reference single-node read)

First single-node read and the template for every `get.py`: `GET /act_<id>` (via `account_path`), comma-joined `fields` param, `check_error`, flatten one node.

**Files:**
- Create: `meta_ads/scripts/accounts/get.py`
- Create: `tests/meta_ads/scripts/test_accounts_get.py`

- [ ] **Step 1: Write failing test.** Write `tests/meta_ads/scripts/test_accounts_get.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.accounts import get as getcmd
from meta_ads.utils.client import MetaAPIError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.accounts.get.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.accounts.get.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_get_normalizes_account_id(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "id": "act_123",
            "name": "Main",
            "currency": "USD",
        }
        with patch.object(
            sys, "argv", ["get.py", "--account-id", "123", "--output", "json"]
        ):
            assert getcmd.main() == 0
        args, kwargs = client.get.call_args
        assert args[0] == "act_123"
        assert "name" in kwargs["params"]["fields"]
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "act_123"
    assert parsed["currency"] == "USD"


def test_get_accepts_prefixed_account_id(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {"id": "act_123", "name": "Main"}
        with patch.object(sys, "argv", ["get.py", "--account-id", "act_123"]):
            assert getcmd.main() == 0
        args, _ = client.get.call_args
        assert args[0] == "act_123"


def test_get_surfaces_api_error(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "error": {"message": "bad", "code": 100, "fbtrace_id": "Z"}
        }
        with (
            patch.object(sys, "argv", ["get.py", "--account-id", "123"]),
            pytest.raises(MetaAPIError),
        ):
            getcmd.main()
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_accounts_get.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `meta_ads/scripts/accounts/get.py`.** Complete code:

```python
"""Get a single Meta ad account by --account-id (with or without act_ prefix)."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, account_path, check_error

_FIELDS = (
    "id,account_id,name,account_status,currency,timezone_name,"
    "amount_spent,balance,business_name,spend_cap"
)


def _flatten(node: dict) -> dict:
    return {
        "id": node.get("id"),
        "account_id": node.get("account_id"),
        "name": node.get("name"),
        "account_status": node.get("account_status"),
        "currency": node.get("currency"),
        "timezone_name": node.get("timezone_name"),
        "amount_spent": node.get("amount_spent"),
        "balance": node.get("balance"),
        "spend_cap": node.get("spend_cap"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get a Meta ad account.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument("--fields", default=_FIELDS)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        body = client.get(account_path(args.account_id), params={"fields": args.fields})

    check_error(body)
    print(format_output(_flatten(body), args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/meta_ads/scripts/test_accounts_get.py -v
uv run ruff check meta_ads/scripts/accounts/get.py tests/meta_ads/scripts/test_accounts_get.py
uv run ruff format meta_ads/scripts/accounts/get.py tests/meta_ads/scripts/test_accounts_get.py
git add meta_ads/scripts/accounts/get.py tests/meta_ads/scripts/test_accounts_get.py
git commit -m "feat(meta-ads): accounts/get.py with act_ normalization + field selection"
```

---

## Task 6: `campaigns/list.py` and `campaigns/get.py`

`campaigns/list.py` lists an account's campaigns (`GET /act_<id>/campaigns`), with an `--account-id` (required) and an optional `--status` effective-status filter (Graph `effective_status` param, JSON-array form). `campaigns/get.py` reads one campaign node.

**Files:**
- Create: `meta_ads/scripts/campaigns/__init__.py`
- Create: `meta_ads/scripts/campaigns/list.py`
- Create: `meta_ads/scripts/campaigns/get.py`
- Create: `tests/meta_ads/scripts/test_campaigns_list.py`
- Create: `tests/meta_ads/scripts/test_campaigns_get.py`

- [ ] **Step 1: Create the campaigns package marker.**

```bash
mkdir -p meta_ads/scripts/campaigns
touch meta_ads/scripts/campaigns/__init__.py
```

- [ ] **Step 2: Write failing tests.** Write `tests/meta_ads/scripts/test_campaigns_list.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from meta_ads.scripts.campaigns import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.campaigns.list.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.campaigns.list.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_campaigns_list_normalizes_account_and_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [
                {
                    "id": "c1",
                    "name": "Spring Sale",
                    "objective": "OUTCOME_SALES",
                    "status": "PAUSED",
                    "effective_status": "PAUSED",
                }
            ]
        )
        with patch.object(
            sys, "argv", ["list.py", "--account-id", "123", "--output", "json"]
        ):
            assert listcmd.main() == 0
        args, _ = client.paginate.call_args
        assert args[0] == "act_123/campaigns"
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "c1"
    assert parsed[0]["objective"] == "OUTCOME_SALES"


def test_campaigns_list_status_filter_builds_param(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(
            sys, "argv", ["list.py", "--account-id", "123", "--status", "ACTIVE"]
        ):
            assert listcmd.main() == 0
        _, kwargs = client.paginate.call_args
        assert kwargs["params"]["effective_status"] == '["ACTIVE"]'
```

Write `tests/meta_ads/scripts/test_campaigns_get.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from meta_ads.scripts.campaigns import get as getcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.campaigns.get.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.campaigns.get.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_campaign_get_by_id(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "id": "c1",
            "name": "Spring Sale",
            "objective": "OUTCOME_SALES",
            "status": "PAUSED",
        }
        with patch.object(
            sys, "argv", ["get.py", "--id", "c1", "--output", "json"]
        ):
            assert getcmd.main() == 0
        args, kwargs = client.get.call_args
        assert args[0] == "c1"
        assert "objective" in kwargs["params"]["fields"]
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "c1"
    assert parsed["status"] == "PAUSED"
```

- [ ] **Step 3: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_campaigns_list.py tests/meta_ads/scripts/test_campaigns_get.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 4: Implement `meta_ads/scripts/campaigns/list.py`.** Complete code:

```python
"""List campaigns under an ad account.

GET /act_<id>/campaigns with field selection, optional --status effective-status
filter (Graph wants a JSON-array string), and cursor pagination capped by --limit.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import json
import sys

from core.config import load_config
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, account_path

_FIELDS = (
    "id,name,objective,status,effective_status,buying_type,"
    "daily_budget,lifetime_budget,start_time,stop_time"
)


def _flatten(node: dict) -> dict:
    return {
        "id": node.get("id"),
        "name": node.get("name"),
        "objective": node.get("objective"),
        "status": node.get("status"),
        "effective_status": node.get("effective_status"),
        "daily_budget": node.get("daily_budget"),
        "lifetime_budget": node.get("lifetime_budget"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List campaigns under an ad account.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument(
        "--status",
        help="Filter by effective_status (e.g. ACTIVE, PAUSED, ARCHIVED)",
    )
    parser.add_argument("--fields", default=_FIELDS)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    params: dict[str, object] = {"fields": args.fields}
    if args.status:
        params["effective_status"] = json.dumps([args.status])

    cfg = load_config(args.config)
    path = f"{account_path(args.account_id)}/campaigns"
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        rows = [_flatten(n) for n in client.paginate(path, params=params, limit=args.limit)]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Implement `meta_ads/scripts/campaigns/get.py`.** Complete code:

```python
"""Get a single campaign node by --id."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, check_error

_FIELDS = (
    "id,name,objective,status,effective_status,buying_type,account_id,"
    "daily_budget,lifetime_budget,budget_remaining,start_time,stop_time,"
    "special_ad_categories,created_time,updated_time"
)


def _flatten(node: dict) -> dict:
    return {
        "id": node.get("id"),
        "name": node.get("name"),
        "objective": node.get("objective"),
        "status": node.get("status"),
        "effective_status": node.get("effective_status"),
        "account_id": node.get("account_id"),
        "daily_budget": node.get("daily_budget"),
        "lifetime_budget": node.get("lifetime_budget"),
        "budget_remaining": node.get("budget_remaining"),
        "start_time": node.get("start_time"),
        "stop_time": node.get("stop_time"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get a campaign by id.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Campaign id")
    parser.add_argument("--fields", default=_FIELDS)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        body = client.get(args.id, params={"fields": args.fields})

    check_error(body)
    print(format_output(_flatten(body), args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/meta_ads/scripts/test_campaigns_list.py tests/meta_ads/scripts/test_campaigns_get.py -v
uv run ruff check meta_ads/scripts/campaigns/ tests/meta_ads/scripts/test_campaigns_list.py tests/meta_ads/scripts/test_campaigns_get.py
uv run ruff format meta_ads/scripts/campaigns/ tests/meta_ads/scripts/test_campaigns_list.py tests/meta_ads/scripts/test_campaigns_get.py
git add meta_ads/scripts/campaigns/__init__.py meta_ads/scripts/campaigns/list.py meta_ads/scripts/campaigns/get.py tests/meta_ads/scripts/test_campaigns_list.py tests/meta_ads/scripts/test_campaigns_get.py
git commit -m "feat(meta-ads): campaigns/list.py (status filter) and campaigns/get.py"
```

---

## Task 7: `adsets/list.py` and `adsets/get.py`

`adsets/list.py` lists ad sets either under an account (`GET /act_<id>/adsets`) or under one campaign (`GET /<campaign_id>/adsets`) — mutually exclusive `--account-id`/`--campaign-id`. `adsets/get.py` reads one ad set node.

**Files:**
- Create: `meta_ads/scripts/adsets/__init__.py`
- Create: `meta_ads/scripts/adsets/list.py`
- Create: `meta_ads/scripts/adsets/get.py`
- Create: `tests/meta_ads/scripts/test_adsets_list.py`
- Create: `tests/meta_ads/scripts/test_adsets_get.py`

- [ ] **Step 1: Create the adsets package marker.**

```bash
mkdir -p meta_ads/scripts/adsets
touch meta_ads/scripts/adsets/__init__.py
```

- [ ] **Step 2: Write failing tests.** Write `tests/meta_ads/scripts/test_adsets_list.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.adsets import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.adsets.list.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.adsets.list.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_adsets_list_under_account(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [{"id": "as1", "name": "Broad", "status": "PAUSED", "campaign_id": "c1"}]
        )
        with patch.object(
            sys, "argv", ["list.py", "--account-id", "123", "--output", "json"]
        ):
            assert listcmd.main() == 0
        args, _ = client.paginate.call_args
        assert args[0] == "act_123/adsets"
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "as1"


def test_adsets_list_under_campaign(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py", "--campaign-id", "c1"]):
            assert listcmd.main() == 0
        args, _ = client.paginate.call_args
        assert args[0] == "c1/adsets"


def test_adsets_list_requires_a_parent(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with (
            patch.object(sys, "argv", ["list.py"]),
            pytest.raises(SystemExit),
        ):
            listcmd.main()
```

Write `tests/meta_ads/scripts/test_adsets_get.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from meta_ads.scripts.adsets import get as getcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.adsets.get.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.adsets.get.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_adset_get_by_id(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "id": "as1",
            "name": "Broad",
            "status": "PAUSED",
            "campaign_id": "c1",
            "optimization_goal": "OFFSITE_CONVERSIONS",
        }
        with patch.object(sys, "argv", ["get.py", "--id", "as1", "--output", "json"]):
            assert getcmd.main() == 0
        args, kwargs = client.get.call_args
        assert args[0] == "as1"
        assert "optimization_goal" in kwargs["params"]["fields"]
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "as1"
    assert parsed["optimization_goal"] == "OFFSITE_CONVERSIONS"
```

- [ ] **Step 3: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_adsets_list.py tests/meta_ads/scripts/test_adsets_get.py -v
```

- [ ] **Step 4: Implement `meta_ads/scripts/adsets/list.py`.** Complete code:

```python
"""List ad sets under an account or one campaign.

Exactly one parent is required: --account-id (GET /act_<id>/adsets) or
--campaign-id (GET /<campaign_id>/adsets). Field selection + cursor pagination.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, account_path

_FIELDS = (
    "id,name,campaign_id,status,effective_status,optimization_goal,"
    "billing_event,daily_budget,lifetime_budget,start_time,end_time"
)


def _flatten(node: dict) -> dict:
    return {
        "id": node.get("id"),
        "name": node.get("name"),
        "campaign_id": node.get("campaign_id"),
        "status": node.get("status"),
        "effective_status": node.get("effective_status"),
        "optimization_goal": node.get("optimization_goal"),
        "daily_budget": node.get("daily_budget"),
        "lifetime_budget": node.get("lifetime_budget"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List ad sets.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id")
    parser.add_argument("--campaign-id", dest="campaign_id")
    parser.add_argument("--fields", default=_FIELDS)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if bool(args.account_id) == bool(args.campaign_id):
        parser.error("exactly one of --account-id or --campaign-id is required")

    if args.account_id:
        path = f"{account_path(args.account_id)}/adsets"
    else:
        path = f"{args.campaign_id}/adsets"

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        rows = [
            _flatten(n)
            for n in client.paginate(path, params={"fields": args.fields}, limit=args.limit)
        ]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Implement `meta_ads/scripts/adsets/get.py`.** Complete code:

```python
"""Get a single ad set node by --id."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, check_error

_FIELDS = (
    "id,name,campaign_id,account_id,status,effective_status,optimization_goal,"
    "billing_event,bid_strategy,bid_amount,daily_budget,lifetime_budget,"
    "budget_remaining,start_time,end_time,targeting,created_time,updated_time"
)


def _flatten(node: dict) -> dict:
    return {
        "id": node.get("id"),
        "name": node.get("name"),
        "campaign_id": node.get("campaign_id"),
        "account_id": node.get("account_id"),
        "status": node.get("status"),
        "effective_status": node.get("effective_status"),
        "optimization_goal": node.get("optimization_goal"),
        "billing_event": node.get("billing_event"),
        "bid_strategy": node.get("bid_strategy"),
        "daily_budget": node.get("daily_budget"),
        "lifetime_budget": node.get("lifetime_budget"),
        "start_time": node.get("start_time"),
        "end_time": node.get("end_time"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get an ad set by id.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Ad set id")
    parser.add_argument("--fields", default=_FIELDS)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        body = client.get(args.id, params={"fields": args.fields})

    check_error(body)
    print(format_output(_flatten(body), args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/meta_ads/scripts/test_adsets_list.py tests/meta_ads/scripts/test_adsets_get.py -v
uv run ruff check meta_ads/scripts/adsets/ tests/meta_ads/scripts/test_adsets_list.py tests/meta_ads/scripts/test_adsets_get.py
uv run ruff format meta_ads/scripts/adsets/ tests/meta_ads/scripts/test_adsets_list.py tests/meta_ads/scripts/test_adsets_get.py
git add meta_ads/scripts/adsets/__init__.py meta_ads/scripts/adsets/list.py meta_ads/scripts/adsets/get.py tests/meta_ads/scripts/test_adsets_list.py tests/meta_ads/scripts/test_adsets_get.py
git commit -m "feat(meta-ads): adsets/list.py (account|campaign parent) and adsets/get.py"
```

---

## Task 8: `ads/list.py` and `ads/get.py`

`ads/list.py` lists ads either under an account (`GET /act_<id>/ads`) or under one ad set (`GET /<adset_id>/ads`) — mutually exclusive `--account-id`/`--adset-id`. `ads/get.py` reads one ad node.

**Files:**
- Create: `meta_ads/scripts/ads/__init__.py`
- Create: `meta_ads/scripts/ads/list.py`
- Create: `meta_ads/scripts/ads/get.py`
- Create: `tests/meta_ads/scripts/test_ads_list.py`
- Create: `tests/meta_ads/scripts/test_ads_get.py`

- [ ] **Step 1: Create the ads package marker.**

```bash
mkdir -p meta_ads/scripts/ads
touch meta_ads/scripts/ads/__init__.py
```

- [ ] **Step 2: Write failing tests.** Write `tests/meta_ads/scripts/test_ads_list.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.ads import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.ads.list.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.ads.list.MetaClient"))
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_ads_list_under_account(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [{"id": "ad1", "name": "Ad One", "status": "PAUSED", "adset_id": "as1"}]
        )
        with patch.object(
            sys, "argv", ["list.py", "--account-id", "123", "--output", "json"]
        ):
            assert listcmd.main() == 0
        args, _ = client.paginate.call_args
        assert args[0] == "act_123/ads"
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "ad1"


def test_ads_list_under_adset(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py", "--adset-id", "as1"]):
            assert listcmd.main() == 0
        args, _ = client.paginate.call_args
        assert args[0] == "as1/ads"


def test_ads_list_requires_a_parent(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with (
            patch.object(sys, "argv", ["list.py"]),
            pytest.raises(SystemExit),
        ):
            listcmd.main()
```

Write `tests/meta_ads/scripts/test_ads_get.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from meta_ads.scripts.ads import get as getcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.ads.get.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.ads.get.MetaClient"))
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_ad_get_by_id(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "id": "ad1",
            "name": "Ad One",
            "status": "PAUSED",
            "adset_id": "as1",
            "creative": {"id": "cr1"},
        }
        with patch.object(sys, "argv", ["get.py", "--id", "ad1", "--output", "json"]):
            assert getcmd.main() == 0
        args, kwargs = client.get.call_args
        assert args[0] == "ad1"
        assert "creative" in kwargs["params"]["fields"]
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "ad1"
    assert parsed["creative_id"] == "cr1"
```

- [ ] **Step 3: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_ads_list.py tests/meta_ads/scripts/test_ads_get.py -v
```

- [ ] **Step 4: Implement `meta_ads/scripts/ads/list.py`.** Complete code:

```python
"""List ads under an account or one ad set.

Exactly one parent is required: --account-id (GET /act_<id>/ads) or --adset-id
(GET /<adset_id>/ads). Field selection + cursor pagination.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, account_path

_FIELDS = "id,name,adset_id,campaign_id,status,effective_status,creative"


def _flatten(node: dict) -> dict:
    creative = node.get("creative") or {}
    return {
        "id": node.get("id"),
        "name": node.get("name"),
        "adset_id": node.get("adset_id"),
        "campaign_id": node.get("campaign_id"),
        "status": node.get("status"),
        "effective_status": node.get("effective_status"),
        "creative_id": creative.get("id"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List ads.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id")
    parser.add_argument("--adset-id", dest="adset_id")
    parser.add_argument("--fields", default=_FIELDS)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if bool(args.account_id) == bool(args.adset_id):
        parser.error("exactly one of --account-id or --adset-id is required")

    if args.account_id:
        path = f"{account_path(args.account_id)}/ads"
    else:
        path = f"{args.adset_id}/ads"

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        rows = [
            _flatten(n)
            for n in client.paginate(path, params={"fields": args.fields}, limit=args.limit)
        ]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Implement `meta_ads/scripts/ads/get.py`.** Complete code:

```python
"""Get a single ad node by --id."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, check_error

_FIELDS = (
    "id,name,adset_id,campaign_id,account_id,status,effective_status,"
    "creative,tracking_specs,created_time,updated_time"
)


def _flatten(node: dict) -> dict:
    creative = node.get("creative") or {}
    return {
        "id": node.get("id"),
        "name": node.get("name"),
        "adset_id": node.get("adset_id"),
        "campaign_id": node.get("campaign_id"),
        "account_id": node.get("account_id"),
        "status": node.get("status"),
        "effective_status": node.get("effective_status"),
        "creative_id": creative.get("id"),
        "created_time": node.get("created_time"),
        "updated_time": node.get("updated_time"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get an ad by id.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Ad id")
    parser.add_argument("--fields", default=_FIELDS)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        body = client.get(args.id, params={"fields": args.fields})

    check_error(body)
    print(format_output(_flatten(body), args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/meta_ads/scripts/test_ads_list.py tests/meta_ads/scripts/test_ads_get.py -v
uv run ruff check meta_ads/scripts/ads/ tests/meta_ads/scripts/test_ads_list.py tests/meta_ads/scripts/test_ads_get.py
uv run ruff format meta_ads/scripts/ads/ tests/meta_ads/scripts/test_ads_list.py tests/meta_ads/scripts/test_ads_get.py
git add meta_ads/scripts/ads/__init__.py meta_ads/scripts/ads/list.py meta_ads/scripts/ads/get.py tests/meta_ads/scripts/test_ads_list.py tests/meta_ads/scripts/test_ads_get.py
git commit -m "feat(meta-ads): ads/list.py (account|adset parent) and ads/get.py"
```

---

## Task 9: `creatives/list.py` and `creatives/get.py`

`creatives/list.py` lists an account's ad creatives (`GET /act_<id>/adcreatives`); `creatives/get.py` reads one creative node.

**Files:**
- Create: `meta_ads/scripts/creatives/__init__.py`
- Create: `meta_ads/scripts/creatives/list.py`
- Create: `meta_ads/scripts/creatives/get.py`
- Create: `tests/meta_ads/scripts/test_creatives_list.py`
- Create: `tests/meta_ads/scripts/test_creatives_get.py`

- [ ] **Step 1: Create the creatives package marker.**

```bash
mkdir -p meta_ads/scripts/creatives
touch meta_ads/scripts/creatives/__init__.py
```

- [ ] **Step 2: Write failing tests.** Write `tests/meta_ads/scripts/test_creatives_list.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from meta_ads.scripts.creatives import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.creatives.list.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.creatives.list.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_creatives_list_normalizes_account(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [{"id": "cr1", "name": "Hero", "object_type": "SHARE", "status": "ACTIVE"}]
        )
        with patch.object(
            sys, "argv", ["list.py", "--account-id", "123", "--output", "json"]
        ):
            assert listcmd.main() == 0
        args, _ = client.paginate.call_args
        assert args[0] == "act_123/adcreatives"
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "cr1"
    assert parsed[0]["object_type"] == "SHARE"
```

Write `tests/meta_ads/scripts/test_creatives_get.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from meta_ads.scripts.creatives import get as getcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.creatives.get.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.creatives.get.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_creative_get_by_id(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "id": "cr1",
            "name": "Hero",
            "object_type": "SHARE",
            "thumbnail_url": "https://x/thumb.png",
        }
        with patch.object(sys, "argv", ["get.py", "--id", "cr1", "--output", "json"]):
            assert getcmd.main() == 0
        args, kwargs = client.get.call_args
        assert args[0] == "cr1"
        assert "thumbnail_url" in kwargs["params"]["fields"]
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "cr1"
    assert parsed["thumbnail_url"] == "https://x/thumb.png"
```

- [ ] **Step 3: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_creatives_list.py tests/meta_ads/scripts/test_creatives_get.py -v
```

- [ ] **Step 4: Implement `meta_ads/scripts/creatives/list.py`.** Complete code:

```python
"""List ad creatives under an ad account (GET /act_<id>/adcreatives)."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, account_path

_FIELDS = "id,name,object_type,status,thumbnail_url,image_hash"


def _flatten(node: dict) -> dict:
    return {
        "id": node.get("id"),
        "name": node.get("name"),
        "object_type": node.get("object_type"),
        "status": node.get("status"),
        "thumbnail_url": node.get("thumbnail_url"),
        "image_hash": node.get("image_hash"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List ad creatives.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument("--fields", default=_FIELDS)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    path = f"{account_path(args.account_id)}/adcreatives"
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        rows = [
            _flatten(n)
            for n in client.paginate(path, params={"fields": args.fields}, limit=args.limit)
        ]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Implement `meta_ads/scripts/creatives/get.py`.** Complete code:

```python
"""Get a single ad creative node by --id."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, check_error

_FIELDS = (
    "id,name,object_type,status,thumbnail_url,image_hash,image_url,"
    "object_story_id,object_story_spec,url_tags,call_to_action_type"
)


def _flatten(node: dict) -> dict:
    return {
        "id": node.get("id"),
        "name": node.get("name"),
        "object_type": node.get("object_type"),
        "status": node.get("status"),
        "thumbnail_url": node.get("thumbnail_url"),
        "image_hash": node.get("image_hash"),
        "object_story_id": node.get("object_story_id"),
        "call_to_action_type": node.get("call_to_action_type"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get an ad creative by id.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Ad creative id")
    parser.add_argument("--fields", default=_FIELDS)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        body = client.get(args.id, params={"fields": args.fields})

    check_error(body)
    print(format_output(_flatten(body), args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/meta_ads/scripts/test_creatives_list.py tests/meta_ads/scripts/test_creatives_get.py -v
uv run ruff check meta_ads/scripts/creatives/ tests/meta_ads/scripts/test_creatives_list.py tests/meta_ads/scripts/test_creatives_get.py
uv run ruff format meta_ads/scripts/creatives/ tests/meta_ads/scripts/test_creatives_list.py tests/meta_ads/scripts/test_creatives_get.py
git add meta_ads/scripts/creatives/__init__.py meta_ads/scripts/creatives/list.py meta_ads/scripts/creatives/get.py tests/meta_ads/scripts/test_creatives_list.py tests/meta_ads/scripts/test_creatives_get.py
git commit -m "feat(meta-ads): creatives/list.py and creatives/get.py"
```

---

## Task 10: `insights/query.py`

`GET /<object_id>/insights` where the object is the account (`act_<id>` via `--account-id`) or any structure node (`--object-id`). Supports `--level {account,campaign,adset,ad}`, mutually exclusive `--date-preset` / `--time-range` (a `{since,until}` JSON string built from `--since`/`--until`), `--breakdowns` (comma-joined), and `--fields` (comma-joined, with a sensible default). Each insights row is already a flat dict of metric values, so the flattener just passes through the requested fields plus any breakdown keys.

**Files:**
- Create: `meta_ads/scripts/insights/__init__.py`
- Create: `meta_ads/scripts/insights/query.py`
- Create: `tests/meta_ads/scripts/test_insights_query.py`

- [ ] **Step 1: Create the insights package marker.**

```bash
mkdir -p meta_ads/scripts/insights
touch meta_ads/scripts/insights/__init__.py
```

- [ ] **Step 2: Write failing test.** Write `tests/meta_ads/scripts/test_insights_query.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.insights import query as querycmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.insights.query.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.insights.query.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_insights_account_node_and_default_params(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [{"impressions": "100", "clicks": "5", "spend": "12.50"}]
        )
        with patch.object(
            sys,
            "argv",
            ["query.py", "--account-id", "123", "--level", "campaign", "--output", "json"],
        ):
            assert querycmd.main() == 0
        args, kwargs = client.paginate.call_args
        assert args[0] == "act_123/insights"
        params = kwargs.get("params") or args[1]
        assert params["level"] == "campaign"
        assert params["date_preset"] == "last_30d"
        assert "impressions" in params["fields"]
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["impressions"] == "100"


def test_insights_object_id_node(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(
            sys, "argv", ["query.py", "--object-id", "c1", "--level", "ad"]
        ):
            assert querycmd.main() == 0
        args, _ = client.paginate.call_args
        assert args[0] == "c1/insights"


def test_insights_time_range_overrides_preset(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(
            sys,
            "argv",
            [
                "query.py",
                "--account-id",
                "123",
                "--since",
                "2026-05-01",
                "--until",
                "2026-05-28",
            ],
        ):
            assert querycmd.main() == 0
        _, kwargs = client.paginate.call_args
        params = kwargs["params"]
        assert params["time_range"] == '{"since": "2026-05-01", "until": "2026-05-28"}'
        assert "date_preset" not in params


def test_insights_breakdowns_passed_through(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(
            sys,
            "argv",
            ["query.py", "--account-id", "123", "--breakdowns", "age,gender"],
        ):
            assert querycmd.main() == 0
        _, kwargs = client.paginate.call_args
        assert kwargs["params"]["breakdowns"] == "age,gender"


def test_insights_requires_a_node(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with (
            patch.object(sys, "argv", ["query.py"]),
            pytest.raises(SystemExit),
        ):
            querycmd.main()


def test_insights_since_and_until_must_pair(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with (
            patch.object(sys, "argv", ["query.py", "--account-id", "123", "--since", "2026-05-01"]),
            pytest.raises(SystemExit),
        ):
            querycmd.main()
```

- [ ] **Step 3: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_insights_query.py -v
```

- [ ] **Step 4: Implement `meta_ads/scripts/insights/query.py`.** Complete code:

```python
"""Query Meta Ads insights for an account or any structure node.

GET /<object_id>/insights. The object node is the account (--account-id, via
act_<id>) or any campaign/adset/ad node (--object-id). Supports --level, a
--date-preset OR a --since/--until time range (mutually exclusive), comma-joined
--breakdowns, and comma-joined --fields. Insights rows are already flat metric
dicts, so each row is emitted as-is (capped by --limit via cursor pagination).
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import json
import sys

from core.config import load_config
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, account_path

_DEFAULT_FIELDS = (
    "impressions,reach,clicks,spend,cpc,cpm,ctr,frequency,"
    "actions,cost_per_action_type"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Query Meta Ads insights.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument(
        "--account-id",
        dest="account_id",
        help="Ad account id (insights node is act_<id>)",
    )
    parser.add_argument(
        "--object-id",
        dest="object_id",
        help="Any campaign/adset/ad node id to pull insights for",
    )
    parser.add_argument(
        "--level",
        choices=("account", "campaign", "adset", "ad"),
        default="account",
        help="Aggregation level of the returned rows",
    )
    parser.add_argument(
        "--date-preset",
        dest="date_preset",
        default="last_30d",
        help="Graph date_preset (ignored when --since/--until are given)",
    )
    parser.add_argument("--since", help="Start date YYYY-MM-DD (requires --until)")
    parser.add_argument("--until", help="End date YYYY-MM-DD (requires --since)")
    parser.add_argument(
        "--breakdowns",
        help="Comma-separated Graph breakdowns (e.g. age,gender)",
    )
    parser.add_argument("--fields", default=_DEFAULT_FIELDS)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if bool(args.account_id) == bool(args.object_id):
        parser.error("exactly one of --account-id or --object-id is required")
    if bool(args.since) != bool(args.until):
        parser.error("--since and --until must be given together")

    node = account_path(args.account_id) if args.account_id else args.object_id
    path = f"{node}/insights"

    params: dict[str, object] = {
        "level": args.level,
        "fields": args.fields,
    }
    if args.since and args.until:
        params["time_range"] = json.dumps({"since": args.since, "until": args.until})
    else:
        params["date_preset"] = args.date_preset
    if args.breakdowns:
        params["breakdowns"] = args.breakdowns

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        rows = list(client.paginate(path, params=params, limit=args.limit))

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/meta_ads/scripts/test_insights_query.py -v
uv run ruff check meta_ads/scripts/insights/ tests/meta_ads/scripts/test_insights_query.py
uv run ruff format meta_ads/scripts/insights/ tests/meta_ads/scripts/test_insights_query.py
git add meta_ads/scripts/insights/__init__.py meta_ads/scripts/insights/query.py tests/meta_ads/scripts/test_insights_query.py
git commit -m "feat(meta-ads): insights/query.py (level, date-preset|time-range, breakdowns, fields)"
```

---

## Task 11: Skills — `meta-ads-structure` (read sections) and `meta-ads-insights`

**Files:**
- Create: `skills/meta-ads-structure/SKILL.md`
- Create: `skills/meta-ads-insights/SKILL.md`

Mirror the `skills/klaviyo-profiles/SKILL.md` front-matter shape: a `name:` line and a single-paragraph `description:` packed with trigger phrases, then a body covering when to use, each script, and the safety posture.

- [ ] **Step 1: Write `skills/meta-ads-structure/SKILL.md`.** Cover the **read** half of the structure cluster: `accounts/{list,get}`, `campaigns/{list,get}`, `adsets/{list,get}`, `ads/{list,get}`, `creatives/{list,get}`. Front-matter `description` must name triggers: "list ad accounts", "show my Meta campaigns", "get a campaign", "list ad sets", "list ads", "show ad creatives", "inspect Meta account structure". Body notes: every script takes `--account-id` (normalized to `act_<id>`), `--fields` for field selection, `--limit`/pagination, `--output {table,json,markdown}`, and `--api-version`. State explicitly that **create/update/pause/activate/delete are deferred to Plan M2** (this skill ships read-only here; the safe-default-`PAUSED` rule applies to the writes that land in M2). Defer Conversions API / catalog management to direct API use.

- [ ] **Step 2: Write `skills/meta-ads-insights/SKILL.md`.** Cover `insights/query`. Triggers: "Meta ads performance", "campaign insights", "ad spend report", "ROAS by campaign", "breakdown by age and gender", "insights for the last 30 days". Body documents `--level {account,campaign,adset,ad}`, `--account-id` vs `--object-id`, `--date-preset` vs `--since`/`--until`, `--breakdowns`, `--fields`, and the `--limit`/`--output` conventions.

- [ ] **Step 3: Commit.**

```bash
git add skills/meta-ads-structure/SKILL.md skills/meta-ads-insights/SKILL.md
git commit -m "docs(meta-ads): meta-ads-structure (reads) and meta-ads-insights skills"
```

---

## Task 12: Full sweep, CHANGELOG, smoke

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Full suite + ruff (with the meta-ads extra installed).**

```bash
uv sync --extra dev --extra shopify --extra webhooks --extra klaviyo --extra meta-ads
uv run pytest tests/ --ignore=tests/shopify/test_whoami_integration.py -v
uv run ruff check .
uv run ruff format --check .
```
Expected: all green; the new `tests/meta_ads/` suite is collected and passes; existing Shopify/Klaviyo tests unaffected.

- [ ] **Step 2: Smoke each script's `--help` and a representative read.**

```bash
uv run meta_ads/scripts/accounts/list.py --help
uv run meta_ads/scripts/campaigns/list.py --help
uv run meta_ads/scripts/adsets/list.py --help
uv run meta_ads/scripts/ads/list.py --help
uv run meta_ads/scripts/creatives/list.py --help
uv run meta_ads/scripts/insights/query.py --help
```
Expected: help text prints for every script (no import errors, all flags registered). Note: live reads need a real `META_ACCESS_TOKEN`; `--help` does not.

- [ ] **Step 3: Update `CHANGELOG.md`.** Add an entry under a new version heading (bump the current `0.8.0` minor line; e.g. `## [0.9.0] — 2026-05-29`) noting: Meta Ads domain foundation (`MetaClient` with Bearer auth, versioned Graph base URL, `act_<id>` normalization, `paging.next` pagination, `check_error`/`MetaAPIError` with `fbtrace_id`; CLI helpers; `meta-ads` extra populated; `domains.meta_ads.api_version` wired; CI `--extra meta-ads`) and the structure-read + insights scripts (`accounts/{list,get}`, `campaigns/{list,get}`, `adsets/{list,get}`, `ads/{list,get}`, `creatives/{list,get}`, `insights/query`). Note the conventions: field selection via `--fields`, `--api-version` override, `--limit`/pagination; writes (safe-default `PAUSED`) and audiences are deferred to Plans M2/M3.

- [ ] **Step 4: Commit.**

```bash
git add CHANGELOG.md
git commit -m "docs(meta-ads): CHANGELOG for Meta Ads foundation + reads + insights (M1)"
```

---

## Definition of Done

(Scoped to M1, per spec §11/§12.)

- [ ] `uv sync --extra meta-ads` installs and every `meta_ads/scripts/{accounts,campaigns,adsets,ads,creatives,insights}/*` script runs (`--help` works).
- [ ] `MetaClient` unit-tested: `Authorization: Bearer <token>` header, versioned base URL (`https://graph.facebook.com/<version>/`) from config `api_version` with `--api-version` override and `_DEFAULT_VERSION` fallback, `account_path` normalizes ids with/without the `act_` prefix, `paginate` follows `paging.next` and respects `--limit`, `check_error` raises `MetaAPIError` carrying `code`/`subcode`/`fbtrace_id` (and names `META_ACCESS_TOKEN` on code 102/190), `delete`/empty body returns `{}`.
- [ ] Structure reads + insights per spec §5 M1: `accounts/{list,get}`, `campaigns/{list,get}`, `adsets/{list,get}`, `ads/{list,get}`, `creatives/{list,get}`, `insights/query`.
- [ ] Reads support `--fields` selection, `--account-id` (normalized) parents (and the `--account-id|--campaign-id` / `--account-id|--adset-id` / `--account-id|--object-id` mutually-exclusive parents where applicable), `--limit`/pagination, and `--output {table,json,markdown}`.
- [ ] `insights/query` supports `--level {account,campaign,adset,ad}`, `--date-preset` OR `--since`/`--until` time range (mutually exclusive, paired), `--breakdowns`, and `--fields`.
- [ ] Per-script unit tests green, mocking `MetaClient` (no live calls); any integration tests gated by `META_INTEGRATION_TESTS=1` and skipped by default.
- [ ] `meta-ads` extra populated in `pyproject.toml`; `domains.meta_ads` wired as `{enabled, api_version}` in `store-config.example.yaml` (the missing `api_version` added); CI installs `--extra meta-ads`.
- [ ] `meta-ads-structure` (read sections) and `meta-ads-insights` skills present and cover their clusters.
- [ ] Full `uv run pytest tests/` green; `ruff check .` and `ruff format --check .` clean. CHANGELOG bumped.
