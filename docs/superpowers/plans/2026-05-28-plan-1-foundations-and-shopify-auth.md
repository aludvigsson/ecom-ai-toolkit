# Plan 1: Foundations + Shopify Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship an installable Claude Code plugin with the `core/` library, packaging, CI, and a working Shopify smoke test (`whoami.py`). After this plan, anyone can clone the repo, install it, fill in credentials, and ask Claude to confirm the shop loads.

**Architecture:** Python 3.12+ monorepo managed by `uv`. `.claude-plugin/` manifest registers skills with Claude Code. `core/` provides the five contracts (`config`, `secrets`, `state`, `http`, `logging`) that every domain depends on. The first domain (`shopify/`) is built with one script (`whoami.py`) and one skill (`shopify-auth`) — proving the pattern end-to-end without breadth.

**Tech Stack:** Python 3.12+, uv, httpx, pydantic v2, pyyaml, pytest, pytest-httpx, ruff, pre-commit, GitHub Actions.

**Spec reference:** `docs/superpowers/specs/2026-05-28-foundations-and-shopify-seed-design.md` (§§ 1–5, 6.1–6.2, 6.5, 6.6 `shopify-auth` only, 8, 9, 10, 11).

---

## File Structure

### Created in this plan

| Path | Responsibility |
|---|---|
| `pyproject.toml` | uv project manifest, deps, extras, ruff + pytest config |
| `.python-version` | Pin Python 3.12 |
| `.pre-commit-config.yaml` | ruff check + format, gitleaks |
| `.github/workflows/ci.yml` | Lint + `tests/core/` on push |
| `LICENSE` | MIT |
| `README.md` | Onboarding §10 of spec |
| `CHANGELOG.md` | keep-a-changelog 0.1.0 |
| `store-config.example.yaml` | Per § 5.1 |
| `.env.example` | Per § 5.2 |
| `.claude-plugin/plugin.json` | Per § 8.2 |
| `.claude-plugin/marketplace.json` | Per § 8.3 |
| `core/__init__.py` | Public API re-exports per § 5.6 |
| `core/logging.py` | `get_logger()` + stdlib config |
| `core/config.py` | `load_config()`, `StoreConfig`, `Market` (pydantic) |
| `core/secrets.py` | `get_secret()`, `require_secret()`, `.env.local` loader |
| `core/state.py` | `load_state()`, `save_state()`, atomic write |
| `core/http.py` | `HttpClient` (httpx.Client subclass) with retry/backoff/redacting logs |
| `shopify/__init__.py` | empty package marker |
| `shopify/utils/__init__.py` | empty |
| `shopify/utils/client.py` | `ShopifyClient` per § 6.5 |
| `shopify/scripts/__init__.py` | empty |
| `shopify/scripts/whoami.py` | Auth smoke test, argparse-driven |
| `skills/shopify-auth/SKILL.md` | First skill per § 6.6 |
| `tests/__init__.py` | empty |
| `tests/core/__init__.py` | empty |
| `tests/core/test_config.py` | Unit tests for config |
| `tests/core/test_secrets.py` | Unit tests for secrets |
| `tests/core/test_state.py` | Unit tests for state |
| `tests/core/test_http.py` | Unit tests for http retry/redact |
| `tests/core/test_logging.py` | Unit tests for logger config |
| `tests/shopify/__init__.py` | empty |
| `tests/shopify/test_client.py` | Unit tests for ShopifyClient (mocked) |
| `tests/shopify/test_whoami_integration.py` | Env-gated integration test |

### Modified

- `.gitignore` — already exists, may add patterns

---

## Task 1: Bootstrap `pyproject.toml` with uv

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`

- [ ] **Step 1: Initialize uv project**

Run:
```bash
cd /Users/andreasl/ecom-ai-toolkit
uv init --no-readme --bare --name ecom-ai-toolkit --python 3.12
```
Expected: creates `pyproject.toml` and `.python-version`. No `src/` layout. No README clobbered.

- [ ] **Step 2: Replace `pyproject.toml` with the project shape**

Overwrite with:
```toml
[project]
name = "ecom-ai-toolkit"
version = "0.1.0"
description = "Python ops scripts + skills for Shopify-centric ecommerce stacks"
readme = "README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
authors = [{ name = "Andreas Ludvigsson" }]
dependencies = []

[project.optional-dependencies]
shopify         = ["httpx>=0.27", "pyyaml>=6", "pydantic>=2.7"]
klaviyo         = []
meta-ads        = []
google-ads      = []
microsoft-ads   = []
merchant-center = []
gtm             = []
webhooks        = ["fastapi>=0.115", "uvicorn[standard]>=0.30"]
all             = ["httpx>=0.27", "pyyaml>=6", "pydantic>=2.7", "fastapi>=0.115", "uvicorn[standard]>=0.30"]
dev = [
  "pytest>=8",
  "pytest-httpx>=0.32",
  "ruff>=0.6",
  "pre-commit>=3",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "SIM"]
ignore = ["E501"]  # handled by formatter

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"
markers = [
  "integration: requires network and credentials; env-gated",
]

[tool.uv]
# Plain library + scripts; no entry points yet.
```

- [ ] **Step 3: Install dev + shopify extras**

Run:
```bash
uv sync --extra dev --extra shopify
```
Expected: creates `uv.lock`, `.venv/`, installs deps. No errors.

- [ ] **Step 4: Verify Python version and pytest available**

Run:
```bash
uv run python --version
uv run pytest --version
uv run ruff --version
```
Expected: Python 3.12.x, pytest 8.x, ruff 0.6+.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .python-version uv.lock
git commit -m "build: bootstrap uv project with shopify and dev extras"
```

---

## Task 2: Pre-commit + ruff config

**Files:**
- Create: `.pre-commit-config.yaml`
- Modify: `.gitignore`

- [ ] **Step 1: Add ignore patterns** (idempotent — patterns may already exist)

Append to `.gitignore` (deduplicated):
```
uv.lock
!uv.lock
node_modules/
.coverage
htmlcov/
```
Note: the `!uv.lock` line ensures we *do* commit it (default ignore patterns don't catch it; this is a reminder for the reader). Actually delete the two `uv.lock` lines if they cause confusion — uv.lock should be committed, just leave `.gitignore` as-is.

Final additions:
```
node_modules/
.coverage
htmlcov/
```

- [ ] **Step 2: Create pre-commit config**

`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.4
    hooks:
      - id: gitleaks
```

- [ ] **Step 3: Install hooks locally**

Run:
```bash
uv run pre-commit install
uv run pre-commit run --all-files
```
Expected: hooks install; first run may auto-fix formatting on whatever files exist. Verify no errors after auto-fix.

- [ ] **Step 4: Commit**

```bash
git add .gitignore .pre-commit-config.yaml
git commit -m "build: pre-commit with ruff and gitleaks"
```

---

## Task 3: Project metadata files

**Files:**
- Create: `LICENSE`
- Create: `README.md`
- Create: `CHANGELOG.md`

- [ ] **Step 1: Write LICENSE (MIT)**

`LICENSE`:
```
MIT License

Copyright (c) 2026 Andreas Ludvigsson

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Write README skeleton**

`README.md`:
```markdown
# ecom-ai-toolkit

Python ops scripts + Claude Code skills for managing a Shopify-centric ecommerce stack.

## Status

v0.1.0 — Foundations + Shopify auth. See `docs/superpowers/plans/` for the implementation roadmap.

## Install

```bash
git clone https://github.com/aludvigsson/ecom-ai-toolkit
cd ecom-ai-toolkit
uv sync --extra shopify              # or --extra all
cp store-config.example.yaml store-config.yaml
cp .env.example .env.local
# Fill in store-config.yaml and .env.local
uv run shopify/scripts/whoami.py
```

## Documentation

- Spec: `docs/superpowers/specs/`
- Plans: `docs/superpowers/plans/`
- Per-domain: `docs/<domain>/` (added in later plans)

## License

MIT
```

- [ ] **Step 3: Write CHANGELOG**

`CHANGELOG.md`:
```markdown
# Changelog

All notable changes documented here. Format follows [keep-a-changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — unreleased

### Added
- Foundations: `core/` (config, secrets, state, http, logging) and packaging.
- Shopify domain skeleton: `ShopifyClient`, `whoami.py` smoke test, `shopify-auth` skill.
- Claude Code plugin manifest declaring `Shopify/Shopify-AI-Toolkit` as dependency.
- CI: lint + core unit tests on push.
```

- [ ] **Step 4: Commit**

```bash
git add LICENSE README.md CHANGELOG.md
git commit -m "docs: add LICENSE, README skeleton, CHANGELOG"
```

---

## Task 4: Example config and secrets

**Files:**
- Create: `store-config.example.yaml`
- Create: `.env.example`

- [ ] **Step 1: Write `store-config.example.yaml`**

```yaml
# Per-store configuration. Copy to store-config.yaml and fill in.
# store-config.yaml is gitignored; this example is committed.

store:
  name: "Example Store"
  primary_domain: example.com
  shopify_domain: example-store.myshopify.com
  storefront_type: online_store_2        # "hydrogen" | "online_store_2"
  default_locale: en-US

markets:
  - code: us
    name: United States
    locale: en-US
    currency: USD
    url_prefix: ""

domains:
  shopify:        { enabled: true,  api_version: "2025-10" }
  klaviyo:        { enabled: false }
  meta_ads:       { enabled: false }
  google_ads:     { enabled: false }
  microsoft_ads:  { enabled: false }
  merchant_center: { enabled: false }
  gtm:            { enabled: false }
```

- [ ] **Step 2: Write `.env.example`**

```
# Per-store secrets. Copy to .env.local and fill in.
# .env.local is gitignored; this example is committed.

# --- Shopify (required for v0.1.0) ---
SHOPIFY_ADMIN_ACCESS_TOKEN=
SHOPIFY_STOREFRONT_ACCESS_TOKEN=
SHOPIFY_WEBHOOK_SECRET=

# --- Reserved namespaces for future domains ---
# Klaviyo
KLAVIYO_PRIVATE_API_KEY=

# Meta
META_ACCESS_TOKEN=
META_BUSINESS_ID=

# Google Ads
GOOGLE_ADS_DEVELOPER_TOKEN=
GOOGLE_ADS_CLIENT_ID=
GOOGLE_ADS_CLIENT_SECRET=
GOOGLE_ADS_REFRESH_TOKEN=
GOOGLE_ADS_LOGIN_CUSTOMER_ID=

# Microsoft Ads
MICROSOFT_ADS_DEVELOPER_TOKEN=
MICROSOFT_ADS_CLIENT_ID=
MICROSOFT_ADS_REFRESH_TOKEN=

# Google Merchant Center
GOOGLE_MERCHANT_ACCOUNT_ID=

# Google Tag Manager
GOOGLE_TAG_MANAGER_ACCOUNT_ID=
```

- [ ] **Step 3: Verify both files are NOT gitignored**

Run:
```bash
git check-ignore store-config.example.yaml .env.example
```
Expected: no output (both should be tracked).

Run:
```bash
git check-ignore store-config.yaml .env.local
```
Expected: each file path printed (both are correctly ignored).

- [ ] **Step 4: Commit**

```bash
git add store-config.example.yaml .env.example
git commit -m "feat: store-config and .env example templates"
```

---

## Task 5: `core/logging.py`

**Files:**
- Create: `core/__init__.py` (empty for now, populated in Task 9)
- Create: `core/logging.py`
- Create: `tests/__init__.py`
- Create: `tests/core/__init__.py`
- Create: `tests/core/test_logging.py`

- [ ] **Step 1: Write failing test**

`tests/core/test_logging.py`:
```python
import logging

from core.logging import get_logger


def test_get_logger_returns_logger_instance():
    log = get_logger("test")
    assert isinstance(log, logging.Logger)


def test_get_logger_name_is_namespaced():
    log = get_logger("ecom.test")
    assert log.name == "ecom.test"


def test_get_logger_is_idempotent():
    a = get_logger("dup")
    b = get_logger("dup")
    assert a is b
```

- [ ] **Step 2: Run test, confirm it fails**

```bash
mkdir -p core tests/core
touch core/__init__.py tests/__init__.py tests/core/__init__.py
uv run pytest tests/core/test_logging.py -v
```
Expected: ImportError or ModuleNotFoundError for `core.logging`.

- [ ] **Step 3: Implement `core/logging.py`**

```python
"""Stdlib logging wrapper. One consistent format across the toolkit."""
from __future__ import annotations

import logging
import os
import sys

_LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s | %(message)s"
_configured = False


def _configure_once() -> None:
    global _configured
    if _configured:
        return
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger. Configures stdlib logging on first call."""
    _configure_once()
    return logging.getLogger(name)
```

- [ ] **Step 4: Run tests, confirm pass**

```bash
uv run pytest tests/core/test_logging.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add core/__init__.py core/logging.py tests/__init__.py tests/core/__init__.py tests/core/test_logging.py
git commit -m "feat(core): logging.get_logger() with stderr stdlib config"
```

---

## Task 6: `core/config.py`

**Files:**
- Create: `core/config.py`
- Create: `tests/core/test_config.py`
- Create: `tests/core/fixtures/valid_config.yaml`
- Create: `tests/core/fixtures/invalid_no_store.yaml`

- [ ] **Step 1: Write fixtures**

`tests/core/fixtures/valid_config.yaml`:
```yaml
store:
  name: "Test Store"
  primary_domain: test.example
  shopify_domain: test-store.myshopify.com
  storefront_type: online_store_2
  default_locale: en-US
markets:
  - code: us
    name: USA
    locale: en-US
    currency: USD
    url_prefix: ""
  - code: se
    name: Sverige
    locale: sv-SE
    currency: SEK
    url_prefix: "/se"
domains:
  shopify:        { enabled: true, api_version: "2025-10" }
  klaviyo:        { enabled: false }
  meta_ads:       { enabled: false }
  google_ads:     { enabled: false }
  microsoft_ads:  { enabled: false }
  merchant_center: { enabled: false }
  gtm:            { enabled: false }
```

`tests/core/fixtures/invalid_no_store.yaml`:
```yaml
markets:
  - code: us
    name: USA
    locale: en-US
    currency: USD
    url_prefix: ""
```

- [ ] **Step 2: Write failing tests**

`tests/core/test_config.py`:
```python
from pathlib import Path

import pytest

from core.config import StoreConfig, load_config

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_valid_config_returns_storeconfig():
    cfg = load_config(FIXTURES / "valid_config.yaml")
    assert isinstance(cfg, StoreConfig)
    assert cfg.store.name == "Test Store"
    assert cfg.store.shopify_domain == "test-store.myshopify.com"


def test_market_lookup_by_code():
    cfg = load_config(FIXTURES / "valid_config.yaml")
    se = cfg.market("se")
    assert se.currency == "SEK"
    assert se.url_prefix == "/se"


def test_market_lookup_missing_raises():
    cfg = load_config(FIXTURES / "valid_config.yaml")
    with pytest.raises(KeyError):
        cfg.market("xx")


def test_domains_enabled():
    cfg = load_config(FIXTURES / "valid_config.yaml")
    assert cfg.domains["shopify"].enabled is True
    assert cfg.domains["klaviyo"].enabled is False


def test_load_missing_file_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.yaml")


def test_load_invalid_yaml_raises_validation(tmp_path):
    # invalid config: missing 'store' section
    with pytest.raises(Exception):
        load_config(FIXTURES / "invalid_no_store.yaml")
```

- [ ] **Step 3: Run tests, confirm fail**

```bash
uv run pytest tests/core/test_config.py -v
```
Expected: ImportError for `core.config`.

- [ ] **Step 4: Implement `core/config.py`**

```python
"""Load and validate store-config.yaml."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class Market(BaseModel):
    code: str
    name: str
    locale: str
    currency: str
    url_prefix: str = ""


class Store(BaseModel):
    name: str
    primary_domain: str
    shopify_domain: str
    storefront_type: Literal["hydrogen", "online_store_2"]
    default_locale: str


class DomainConfig(BaseModel):
    enabled: bool = False
    api_version: str | None = None


class StoreConfig(BaseModel):
    store: Store
    markets: list[Market] = Field(default_factory=list)
    domains: dict[str, DomainConfig] = Field(default_factory=dict)

    def market(self, code: str) -> Market:
        for m in self.markets:
            if m.code == code:
                return m
        raise KeyError(f"No market with code={code!r} in store-config.yaml")


def load_config(path: str | Path = "store-config.yaml") -> StoreConfig:
    """Load and validate a store-config.yaml file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"store-config not found at {p}. "
            f"Copy store-config.example.yaml to store-config.yaml and edit."
        )
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    return StoreConfig.model_validate(raw)
```

- [ ] **Step 5: Run tests, confirm pass**

```bash
uv run pytest tests/core/test_config.py -v
```
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add core/config.py tests/core/test_config.py tests/core/fixtures/
git commit -m "feat(core): config.load_config() with pydantic validation"
```

---

## Task 7: `core/secrets.py`

**Files:**
- Create: `core/secrets.py`
- Create: `tests/core/test_secrets.py`

- [ ] **Step 1: Write failing tests**

`tests/core/test_secrets.py`:
```python
import pytest

from core.secrets import MissingSecretError, get_secret, require_secret


def test_get_secret_returns_value(monkeypatch):
    monkeypatch.setenv("FOO_TOKEN", "abc123")
    assert get_secret("FOO_TOKEN") == "abc123"


def test_get_secret_missing_returns_none(monkeypatch):
    monkeypatch.delenv("FOO_TOKEN", raising=False)
    assert get_secret("FOO_TOKEN") is None


def test_require_secret_present(monkeypatch):
    monkeypatch.setenv("BAR_KEY", "xyz")
    assert require_secret("BAR_KEY") == "xyz"


def test_require_secret_missing_raises_with_helpful_message(monkeypatch):
    monkeypatch.delenv("BAR_KEY", raising=False)
    with pytest.raises(MissingSecretError) as exc:
        require_secret("BAR_KEY")
    msg = str(exc.value)
    assert "BAR_KEY" in msg
    assert ".env.local" in msg


def test_load_env_local_populates_environ(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.local").write_text("LOADED_KEY=loaded_value\n")
    monkeypatch.delenv("LOADED_KEY", raising=False)
    from core.secrets import load_env_local
    load_env_local()
    import os
    assert os.environ.get("LOADED_KEY") == "loaded_value"
```

- [ ] **Step 2: Run tests, confirm fail**

```bash
uv run pytest tests/core/test_secrets.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement `core/secrets.py`**

```python
"""Load and access per-store secrets from .env.local."""
from __future__ import annotations

import os
from pathlib import Path


class MissingSecretError(RuntimeError):
    """Raised when a required secret is not set."""


_env_loaded = False


def load_env_local(path: str | Path = ".env.local") -> None:
    """Parse a simple KEY=value .env file and set into os.environ.

    Lines starting with '#' and blank lines are skipped. Values are not
    quoted/expanded. Subsequent calls are idempotent.
    """
    global _env_loaded
    p = Path(path)
    if not p.exists():
        _env_loaded = True
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        # Don't clobber values already set in the real environment.
        os.environ.setdefault(key, value)
    _env_loaded = True


def _ensure_loaded() -> None:
    if not _env_loaded:
        load_env_local()


def get_secret(name: str) -> str | None:
    """Return a secret from the environment (loading .env.local first), or None."""
    _ensure_loaded()
    return os.environ.get(name) or None


def require_secret(name: str) -> str:
    """Return a secret or raise a clear MissingSecretError pointing at .env.local."""
    value = get_secret(name)
    if not value:
        raise MissingSecretError(
            f"Missing required secret {name!r}. "
            f"Add it to .env.local (see .env.example for the full list)."
        )
    return value
```

- [ ] **Step 4: Run tests, confirm pass**

```bash
uv run pytest tests/core/test_secrets.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add core/secrets.py tests/core/test_secrets.py
git commit -m "feat(core): secrets loader for .env.local with require_secret"
```

---

## Task 8: `core/state.py`

**Files:**
- Create: `core/state.py`
- Create: `tests/core/test_state.py`

- [ ] **Step 1: Write failing tests**

`tests/core/test_state.py`:
```python
from pathlib import Path

from core.state import load_state, save_state


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data = {"hello": "world", "n": 42, "items": [1, 2, 3]}
    save_state("shopify", "demo", data)
    assert load_state("shopify", "demo") == data


def test_load_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert load_state("shopify", "never_saved") is None


def test_state_files_go_under_dot_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_state("klaviyo", "campaign_42", {"ok": True})
    assert (tmp_path / ".state" / "klaviyo" / "campaign_42.json").exists()


def test_save_is_atomic(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_state("shopify", "a", {"v": 1})
    # No tmp file should remain after a successful save.
    tmps = list((tmp_path / ".state" / "shopify").glob("*.tmp*"))
    assert tmps == []
```

- [ ] **Step 2: Run tests, confirm fail**

```bash
uv run pytest tests/core/test_state.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement `core/state.py`**

```python
"""Per-domain idempotency / audit state under .state/<domain>/<name>.json."""
from __future__ import annotations

import json
import os
from pathlib import Path

STATE_ROOT = Path(".state")


def _path(domain: str, name: str) -> Path:
    return STATE_ROOT / domain / f"{name}.json"


def load_state(domain: str, name: str) -> dict | None:
    """Return the parsed JSON state file, or None if missing."""
    p = _path(domain, name)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(domain: str, name: str, data: dict) -> None:
    """Atomically write a state file (tmp + os.replace)."""
    p = _path(domain, name)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, p)
```

- [ ] **Step 4: Run tests, confirm pass**

```bash
uv run pytest tests/core/test_state.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add core/state.py tests/core/test_state.py
git commit -m "feat(core): state load_state/save_state with atomic writes"
```

---

## Task 9: `core/http.py` + populate `core/__init__.py`

**Files:**
- Create: `core/http.py`
- Modify: `core/__init__.py`
- Create: `tests/core/test_http.py`

- [ ] **Step 1: Write failing tests**

`tests/core/test_http.py`:
```python
import logging

import httpx
import pytest

from core.http import HttpClient


def test_get_succeeds_on_200(httpx_mock):
    httpx_mock.add_response(method="GET", url="https://example.test/ok", json={"ok": True})
    client = HttpClient(base_url="https://example.test")
    r = client.get("/ok")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_retries_on_429_then_succeeds(httpx_mock):
    httpx_mock.add_response(method="GET", url="https://example.test/x", status_code=429, headers={"Retry-After": "0"})
    httpx_mock.add_response(method="GET", url="https://example.test/x", json={"ok": True})
    client = HttpClient(base_url="https://example.test", max_retries=3, backoff_base=0.0)
    r = client.get("/x")
    assert r.status_code == 200


def test_retries_on_5xx_then_succeeds(httpx_mock):
    httpx_mock.add_response(method="GET", url="https://example.test/y", status_code=503)
    httpx_mock.add_response(method="GET", url="https://example.test/y", status_code=502)
    httpx_mock.add_response(method="GET", url="https://example.test/y", json={"ok": True})
    client = HttpClient(base_url="https://example.test", max_retries=5, backoff_base=0.0)
    r = client.get("/y")
    assert r.status_code == 200


def test_gives_up_after_max_retries(httpx_mock):
    for _ in range(4):
        httpx_mock.add_response(method="GET", url="https://example.test/z", status_code=503)
    client = HttpClient(base_url="https://example.test", max_retries=3, backoff_base=0.0)
    with pytest.raises(httpx.HTTPStatusError):
        client.get("/z")


def test_authorization_header_is_redacted_in_logs(httpx_mock, caplog):
    httpx_mock.add_response(method="GET", url="https://example.test/a", json={"ok": True})
    client = HttpClient(base_url="https://example.test", default_headers={"Authorization": "Bearer SECRET"})
    with caplog.at_level(logging.INFO, logger="ecom.http"):
        client.get("/a")
    log_text = "\n".join(r.message for r in caplog.records)
    assert "SECRET" not in log_text
```

- [ ] **Step 2: Run tests, confirm fail**

```bash
uv run pytest tests/core/test_http.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement `core/http.py`**

```python
"""HTTP client with retry/backoff/redacting logs. Every domain client builds on this."""
from __future__ import annotations

import logging
import random
import time
from typing import Any

import httpx

from core.logging import get_logger

_log = get_logger("ecom.http")

_RETRY_STATUSES = {429, 500, 502, 503, 504}


class HttpClient:
    """Thin httpx.Client wrapper with retry, backoff, and log redaction.

    Subclass per domain (e.g. ShopifyClient) and add high-level methods.
    """

    def __init__(
        self,
        *,
        base_url: str = "",
        default_headers: dict[str, str] | None = None,
        max_retries: int = 4,
        backoff_base: float = 0.5,
        backoff_max: float = 30.0,
        timeout: float = 30.0,
    ) -> None:
        self._client = httpx.Client(base_url=base_url, headers=default_headers or {}, timeout=timeout)
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._backoff_max = backoff_max

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        attempt = 0
        while True:
            response = self._client.request(method, url, **kwargs)
            self._log_request(response)
            if response.status_code not in _RETRY_STATUSES or attempt >= self._max_retries:
                response.raise_for_status()
                return response
            delay = self._compute_delay(response, attempt)
            _log.warning(
                "http retry attempt=%d status=%d sleep=%.2fs url=%s",
                attempt + 1, response.status_code, delay, url,
            )
            time.sleep(delay)
            attempt += 1

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def _compute_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
        # Exponential backoff with full jitter, capped.
        exp = self._backoff_base * (2 ** attempt)
        return min(self._backoff_max, random.uniform(0, exp))

    def _log_request(self, response: httpx.Response) -> None:
        req = response.request
        _log.info(
            "http %s %s -> %d in %.0fms",
            req.method,
            f"{req.url.host}{req.url.path}",
            response.status_code,
            response.elapsed.total_seconds() * 1000,
        )


class _RedactingFilter(logging.Filter):
    """Ensures Authorization / token / api-key values never appear in log output."""

    _SENSITIVE_KEYS = ("authorization", "token", "api-key", "x-api-key")

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage().lower()
        for k in self._SENSITIVE_KEYS:
            if k in msg:
                record.msg = "[redacted sensitive log line]"
                record.args = ()
                return True
        return True


_log.addFilter(_RedactingFilter())
```

- [ ] **Step 4: Update `core/__init__.py` to expose public API**

`core/__init__.py`:
```python
"""ecom-ai-toolkit core. Public API used by all domains."""
from core.config import Market, Store, StoreConfig, load_config
from core.http import HttpClient
from core.logging import get_logger
from core.secrets import MissingSecretError, get_secret, require_secret
from core.state import load_state, save_state

__all__ = [
    "HttpClient",
    "Market",
    "MissingSecretError",
    "Store",
    "StoreConfig",
    "get_logger",
    "get_secret",
    "load_config",
    "load_state",
    "require_secret",
    "save_state",
]
```

- [ ] **Step 5: Run tests, confirm pass**

```bash
uv run pytest tests/core/ -v
```
Expected: all core tests pass (logging 3 + config 6 + secrets 5 + state 4 + http 5 = 23).

- [ ] **Step 6: Commit**

```bash
git add core/http.py core/__init__.py tests/core/test_http.py
git commit -m "feat(core): HttpClient with retry/backoff/redacting logs"
```

---

## Task 10: `.claude-plugin/` manifests

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Write `plugin.json`**

```json
{
  "name": "ecom-ai-toolkit",
  "version": "0.1.0",
  "description": "Python ops scripts + skills for Shopify-centric ecommerce stacks",
  "author": {
    "name": "Andreas Ludvigsson"
  },
  "license": "MIT",
  "dependencies": {
    "Shopify/Shopify-AI-Toolkit": "^1.0.0"
  },
  "skills": "./skills"
}
```

- [ ] **Step 2: Write `marketplace.json`**

```json
{
  "$schema": "https://raw.githubusercontent.com/anthropics/claude-code-marketplace/main/schemas/marketplace.json",
  "name": "ecom-ai-toolkit",
  "description": "Python ops scripts + skills for Shopify-centric ecommerce stacks",
  "homepage": "https://github.com/aludvigsson/ecom-ai-toolkit",
  "repository": "https://github.com/aludvigsson/ecom-ai-toolkit",
  "license": "MIT"
}
```

> **Note for executor:** if Claude Code's plugin manifest schema has evolved since this plan was written, follow current docs. The intent is: a v0.1.0 plugin that pulls in `Shopify/Shopify-AI-Toolkit` and exposes a `skills/` directory.

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "feat: Claude Code plugin manifest with Shopify-AI-Toolkit dep"
```

---

## Task 11: `shopify/utils/client.py` — ShopifyClient

**Files:**
- Create: `shopify/__init__.py`
- Create: `shopify/utils/__init__.py`
- Create: `shopify/utils/client.py`
- Create: `tests/shopify/__init__.py`
- Create: `tests/shopify/test_client.py`

- [ ] **Step 1: Write failing tests**

`tests/shopify/test_client.py`:
```python
import pytest

from core.config import StoreConfig
from shopify.utils.client import ShopifyClient, ShopifyGraphQLError

_CFG_DICT = {
    "store": {
        "name": "Test", "primary_domain": "test.example",
        "shopify_domain": "test-store.myshopify.com",
        "storefront_type": "online_store_2", "default_locale": "en-US",
    },
    "markets": [],
    "domains": {"shopify": {"enabled": True, "api_version": "2025-10"}},
}


@pytest.fixture
def cfg():
    return StoreConfig.model_validate(_CFG_DICT)


def test_graphql_returns_data(httpx_mock, monkeypatch, cfg):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_test")
    httpx_mock.add_response(
        method="POST",
        url="https://test-store.myshopify.com/admin/api/2025-10/graphql.json",
        json={"data": {"shop": {"name": "Test"}}, "extensions": {"cost": {"actualQueryCost": 1}}},
    )
    client = ShopifyClient(config=cfg)
    result = client.graphql("query { shop { name } }")
    assert result["shop"]["name"] == "Test"


def test_graphql_user_errors_raise(httpx_mock, monkeypatch, cfg):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_test")
    httpx_mock.add_response(
        method="POST",
        url="https://test-store.myshopify.com/admin/api/2025-10/graphql.json",
        json={"errors": [{"message": "Field 'foo' doesn't exist"}]},
    )
    client = ShopifyClient(config=cfg)
    with pytest.raises(ShopifyGraphQLError) as exc:
        client.graphql("query { foo }")
    assert "doesn't exist" in str(exc.value)


def test_missing_token_raises(monkeypatch, cfg):
    monkeypatch.delenv("SHOPIFY_ADMIN_ACCESS_TOKEN", raising=False)
    with pytest.raises(Exception) as exc:
        ShopifyClient(config=cfg)
    assert "SHOPIFY_ADMIN_ACCESS_TOKEN" in str(exc.value)
```

- [ ] **Step 2: Run tests, confirm fail**

```bash
mkdir -p shopify/utils shopify/scripts tests/shopify
touch shopify/__init__.py shopify/utils/__init__.py shopify/scripts/__init__.py tests/shopify/__init__.py
uv run pytest tests/shopify/test_client.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement `shopify/utils/client.py`**

```python
"""Shopify Admin GraphQL client built on core.http.HttpClient."""
from __future__ import annotations

from typing import Any

from core.config import StoreConfig
from core.http import HttpClient
from core.logging import get_logger
from core.secrets import require_secret

_log = get_logger("ecom.shopify.client")


class ShopifyGraphQLError(RuntimeError):
    """GraphQL `errors` array was non-empty."""


class ShopifyClient:
    """Admin GraphQL client.

    Reads SHOPIFY_ADMIN_ACCESS_TOKEN from the environment at construction time.
    """

    def __init__(self, config: StoreConfig) -> None:
        self._config = config
        token = require_secret("SHOPIFY_ADMIN_ACCESS_TOKEN")
        domain = config.store.shopify_domain
        api_version = config.domains["shopify"].api_version or "2025-10"
        self._endpoint = (
            f"https://{domain}/admin/api/{api_version}/graphql.json"
        )
        self._http = HttpClient(
            default_headers={
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    @property
    def shop_domain(self) -> str:
        return self._config.store.shopify_domain

    def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GraphQL operation and return the `data` block."""
        payload = {"query": query, "variables": variables or {}}
        response = self._http.post(self._endpoint, json=payload)
        body = response.json()
        if body.get("errors"):
            raise ShopifyGraphQLError(
                "; ".join(e.get("message", str(e)) for e in body["errors"])
            )
        return body.get("data", {})

    def close(self) -> None:
        self._http.close()
```

- [ ] **Step 4: Run tests, confirm pass**

```bash
uv run pytest tests/shopify/test_client.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add shopify/ tests/shopify/__init__.py tests/shopify/test_client.py
git commit -m "feat(shopify): ShopifyClient with Admin GraphQL + error mapping"
```

---

## Task 12: `shopify/scripts/whoami.py`

**Files:**
- Create: `shopify/scripts/whoami.py`
- Create: `tests/shopify/test_whoami.py`

- [ ] **Step 1: Write failing test (unit, no network)**

`tests/shopify/test_whoami.py`:
```python
import sys
from unittest.mock import patch

from shopify.scripts import whoami


def test_whoami_prints_shop_name(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    monkeypatch.chdir(monkeypatch.helpers if False else ".")
    fake_data = {"shop": {"name": "My Test Shop", "primaryDomain": {"url": "https://x.com"}, "plan": {"displayName": "Basic"}}}
    with patch("shopify.scripts.whoami.load_config") as mock_cfg, \
         patch("shopify.scripts.whoami.ShopifyClient") as mock_client:
        mock_cfg.return_value.store.shopify_domain = "x.myshopify.com"
        mock_cfg.return_value.domains = {"shopify": type("D", (), {"api_version": "2025-10", "enabled": True})()}
        mock_client.return_value.graphql.return_value = fake_data
        with patch.object(sys, "argv", ["whoami.py"]):
            whoami.main()
    out = capsys.readouterr().out
    assert "My Test Shop" in out
```

- [ ] **Step 2: Run test, confirm fail**

```bash
uv run pytest tests/shopify/test_whoami.py -v
```
Expected: ImportError or AttributeError (no `main` yet).

- [ ] **Step 3: Implement `shopify/scripts/whoami.py`**

```python
"""Auth smoke test. Prints shop name, primary domain, and plan."""
from __future__ import annotations

import argparse
import json
import sys

from core.config import load_config
from core.logging import get_logger
from shopify.utils.client import ShopifyClient

_log = get_logger("ecom.shopify.whoami")

_QUERY = """
query { shop { name primaryDomain { url } plan { displayName } } }
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Shopify Admin API authentication.")
    parser.add_argument("--config", default="store-config.yaml", help="Path to store-config.yaml")
    parser.add_argument("--output", choices=("table", "json"), default="table")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    client = ShopifyClient(config=cfg)
    try:
        data = client.graphql(_QUERY)
    finally:
        client.close()

    shop = data["shop"]
    if args.output == "json":
        print(json.dumps(shop, indent=2))
    else:
        print(f"Shop:    {shop['name']}")
        print(f"Domain:  {shop['primaryDomain']['url']}")
        print(f"Plan:    {shop['plan']['displayName']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/shopify/ -v
```
Expected: 4 passed (3 client + 1 whoami).

- [ ] **Step 5: Commit**

```bash
git add shopify/scripts/whoami.py tests/shopify/test_whoami.py
git commit -m "feat(shopify): whoami.py auth smoke test"
```

---

## Task 13: `skills/shopify-auth/SKILL.md`

**Files:**
- Create: `skills/shopify-auth/SKILL.md`

- [ ] **Step 1: Write the skill**

```markdown
---
name: shopify-auth
description: Verify Shopify Admin API authentication for the current store and walk a new user through first-time setup. Use when the user says the toolkit isn't working, gets an auth error, or asks "is my Shopify connected?". Also runs as the very first thing on a fresh install before any other Shopify skill.
---

# shopify-auth

## When to use

- New install: user has just cloned the repo and needs to verify their setup before doing anything else.
- Any Shopify script fails with an auth-shaped error (`MissingSecretError`, 401, "Invalid API key or access token").
- User explicitly asks: "is my shop connected?" / "test my Shopify creds" / "whoami".

## When NOT to use

- The user has a real Shopify question (products, orders, etc.). Delegate to the appropriate Shopify skill (`shopify-products`, `shopify-orders`, …). Don't pre-emptively run whoami on every request.

## Prerequisites

- `store-config.yaml` exists at repo root and has `store.shopify_domain` set.
- `.env.local` exists at repo root and has `SHOPIFY_ADMIN_ACCESS_TOKEN` set.
- Project deps installed: `uv sync --extra shopify`.

If either of the files above is missing, walk the user through copying the `.example` versions and filling them in. Do NOT proceed to running whoami until they confirm both files exist.

## Canonical workflow

```bash
uv run shopify/scripts/whoami.py
```

Expected output:
```
Shop:    <Store name>
Domain:  https://<their-domain>
Plan:    <Shopify plan>
```

If the user wants JSON: `uv run shopify/scripts/whoami.py --output json`.

## Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `MissingSecretError: SHOPIFY_ADMIN_ACCESS_TOKEN` | `.env.local` missing or token unset | Copy `.env.example` to `.env.local`, fill in token |
| `FileNotFoundError: store-config not found` | First-time install hasn't been completed | Copy `store-config.example.yaml` to `store-config.yaml` and fill in |
| `ShopifyGraphQLError: Invalid API key or access token` | Token wrong scope or expired | Regenerate token in Shopify admin: Settings → Apps → Develop apps → your app → API credentials. Token must be a custom-app *Admin API access token*, not a Storefront token. |
| `401` with no GraphQL error | Wrong header — likely using Storefront token | Confirm it's a token starting with `shpat_` (Admin API), not `shpsst_` (Storefront) |

## Reference

For full Admin API schema and capability questions, defer to the `shopify-plugin:shopify-admin` skill from the Shopify-AI-Toolkit plugin dependency.
```

- [ ] **Step 2: Commit**

```bash
git add skills/shopify-auth/SKILL.md
git commit -m "feat(skills): shopify-auth — first-run verification + auth troubleshooting"
```

---

## Task 14: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write CI workflow**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - name: Set up Python
        run: uv python install 3.12
      - name: Sync deps
        run: uv sync --extra dev --extra shopify
      - name: Ruff check
        run: uv run ruff check .
      - name: Ruff format check
        run: uv run ruff format --check .
      - name: Run core + shopify unit tests
        run: uv run pytest tests/core tests/shopify --ignore=tests/shopify/test_whoami_integration.py
```

- [ ] **Step 2: Lint locally first**

Run:
```bash
uv run ruff check .
uv run ruff format --check .
```
Expected: clean. Fix anything that's flagged before committing.

- [ ] **Step 3: Run the full test suite locally**

```bash
uv run pytest -v
```
Expected: all unit tests pass (~24).

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: lint + unit tests on push and PR"
```

---

## Task 15: Integration test for `whoami.py` (env-gated)

**Files:**
- Create: `tests/shopify/test_whoami_integration.py`

- [ ] **Step 1: Write the env-gated test**

```python
"""Integration test against a real Shopify dev shop.

Skipped unless SHOPIFY_INTEGRATION_TESTS=1 is set. Requires:
  - store-config.yaml pointing at a dev shop
  - SHOPIFY_ADMIN_ACCESS_TOKEN in .env.local
"""
from __future__ import annotations

import os

import pytest

from shopify.scripts import whoami

pytestmark = pytest.mark.skipif(
    os.environ.get("SHOPIFY_INTEGRATION_TESTS") != "1",
    reason="set SHOPIFY_INTEGRATION_TESTS=1 to run",
)


@pytest.mark.integration
def test_whoami_against_real_shop(capsys):
    rc = whoami.main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Shop:" in out
    assert "Domain:" in out
    assert "Plan:" in out
```

- [ ] **Step 2: Verify it's skipped without env var**

```bash
uv run pytest tests/shopify/test_whoami_integration.py -v
```
Expected: 1 skipped.

- [ ] **Step 3: (Manual) verify integration locally if a dev shop is available**

If you have a dev shop:
```bash
SHOPIFY_INTEGRATION_TESTS=1 uv run pytest tests/shopify/test_whoami_integration.py -v
```
Expected: 1 passed, prints shop info.

If no dev shop available, document this in the commit message and move on.

- [ ] **Step 4: Commit**

```bash
git add tests/shopify/test_whoami_integration.py
git commit -m "test(shopify): env-gated integration test for whoami.py"
```

---

## Task 16: README onboarding pass + final lint

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace README with full onboarding (spec § 10)**

```markdown
# ecom-ai-toolkit

Python ops scripts + Claude Code skills for managing a Shopify-centric ecommerce stack.

## Status

v0.1.0 — Foundations + Shopify auth. Future plans (catalog, commerce, storefront, webhooks) are documented under `docs/superpowers/plans/`.

## Install — first 5 minutes

```bash
# 1. clone + sync
git clone https://github.com/aludvigsson/ecom-ai-toolkit && cd ecom-ai-toolkit
uv sync --extra shopify          # or --extra all when other domains land

# 2. fill in per-store config (gitignored)
cp store-config.example.yaml store-config.yaml
cp .env.example .env.local
# Edit both with your store's domain, locale, and Admin API token.

# 3. verify auth
uv run shopify/scripts/whoami.py
# Expect: shop name, primary domain, plan printed.

# 4. (optional) install the plugin in Claude Code so skills auto-load
# Inside the repo:
#   claude
# Then ask: "verify my Shopify connection"
```

## Repo layout

```
core/                  # Shared library: config, secrets, state, http, logging
shopify/               # Shopify domain: utils/client.py + scripts/
skills/                # Claude Code skills (kebab-case)
.claude-plugin/        # Plugin manifest (depends on Shopify/Shopify-AI-Toolkit)
docs/superpowers/      # Specs + plans
tests/                 # core/ unit tests + per-domain integration tests
```

## Adding a domain (future plans)

See `docs/superpowers/specs/2026-05-28-foundations-and-shopify-seed-design.md` § 7 ("Extension pattern").

## License

MIT
```

- [ ] **Step 2: Full sweep — lint + format + tests**

```bash
uv run ruff check . --fix
uv run ruff format .
uv run pytest -v
```
Expected: clean lint, format applied (likely no changes), all tests pass.

- [ ] **Step 3: Commit**

```bash
git add README.md
# include any auto-formatter changes
git add -u
git commit -m "docs: fill out README onboarding for v0.1.0"
```

- [ ] **Step 4: Tag the release point** (optional but recommended)

```bash
git tag -a v0.1.0-alpha -m "Foundations + Shopify auth"
git log --oneline -20
```

---

## Definition of Done

- [ ] `uv sync --extra dev --extra shopify` succeeds in a fresh clone.
- [ ] `uv run pytest -v` passes; all `tests/core/` + `tests/shopify/test_client.py` + `tests/shopify/test_whoami.py` green; integration test skipped.
- [ ] `uv run ruff check .` and `uv run ruff format --check .` both clean.
- [ ] `uv run shopify/scripts/whoami.py` against a real dev shop prints shop name (manual verification).
- [ ] `.claude-plugin/plugin.json` parses; Claude Code recognizes the plugin if dropped into a `claude` session in this repo.
- [ ] GitHub Actions workflow runs on push and goes green.
- [ ] All 16 tasks committed; commit log is clean and follows conventional prefixes (`feat:`, `docs:`, `build:`, `ci:`, `test:`).
