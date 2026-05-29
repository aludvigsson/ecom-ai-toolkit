# Plan M3: Meta Ads Audiences Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the Meta Ads audiences cluster — `audiences/{list,get,create,create_lookalike,add_users,remove_users,delete}` — so custom audiences, lookalikes, and customer-file membership can be managed from `uv run meta_ads/scripts/audiences/<op>.py`, with SHA-256-hashed identifiers, safe-default `--dry-run`, and `--yes` gating on every membership change and deletion.

**Architecture:** All scripts reuse the M1 foundation: `MetaClient` (Graph API over `core.http.HttpClient`, Bearer auth, versioned base URL, `act_<id>` normalization, `paging.next` pagination, `check_error`/`MetaAPIError`) and `meta_ads/utils/cli.py` (`add_common_flags`/`add_meta_flags`/`configure_logging_from_args`/`format_output`). Audience membership writes hash identifiers with `hashlib.sha256` and send them in the Graph `payload` form param (a JSON-encoded `{schema, data}` object); `add_users` POSTs to `/<audience_id>/users`, while `remove_users` issues a `DELETE` to `/<audience_id>/users` carrying the same `payload` as a form/query param (NOT a JSON body — spec §5 M3 note). Reads flatten Graph audience nodes into flat rows; every mutation supports `--dry-run` (prints the Graph request, exits 0); `add_users`/`remove_users`/`delete` are `--yes`-gated.

**Tech Stack:** stdlib `hashlib` (SHA-256) + the existing base deps (`httpx>=0.27`, `pyyaml>=6`, `pydantic>=2.7`, already populated for the `meta-ads` extra in M1). Tests use `pytest` with `monkeypatch`/`unittest.mock.patch`. No vendor SDK (`facebook-business`), no MCP.

**Spec reference:** `docs/superpowers/specs/2026-05-29-meta-ads-domain-design.md` §5 M3 (audiences script inventory, including the `remove_users` DELETE-with-`payload`-form note), §4 (conventions — safe-default writes, `--yes` gates, `--limit`/pagination), §6 (data flow), §7 (error handling), §10 (skills), §11 (implementation split — Plan M3), §12 (definition of done).

**Depends on:** **Plan M1** (`meta_ads/utils/client.py` `MetaClient`/`account_path`/`check_error`/`MetaAPIError`, `meta_ads/utils/cli.py`, the `meta-ads` extra, `domains.meta_ads.api_version` wiring, CI `--extra meta-ads`, and the `tests/meta_ads/` package). No `core/` changes. M3 adds no client methods — `MetaClient.post`/`delete` already exist from M1; this plan only adds the `audiences/` scripts, their tests, the `meta-ads-audiences` skill, and the CHANGELOG/version bump.

> **Scope note — payload hashing & the `remove_users` DELETE shape:** Meta's customer-file matching requires identifiers (email/phone) to be **lowercased, trimmed, then SHA-256-hashed** before transmission. Both membership scripts build a `payload` object `{"schema": "<SCHEMA>", "data": [[<hash>], ...]}` and pass it JSON-encoded as the Graph `payload` param. `add_users` sends it in the **POST form body**; `remove_users` uses **`DELETE /<audience_id>/users` with `payload` as a form/query param** (`client.delete(path, params={"payload": ...})`), **not** a JSON body. Tests assert the hashing (lowercased input hashed) and the verb/transport per script.

---

## File Structure

| Path | Responsibility |
|---|---|
| `meta_ads/scripts/audiences/__init__.py` | empty package marker |
| `meta_ads/scripts/audiences/list.py` | `GET /act_<id>/customaudiences` — `--account-id`, field selection, pagination |
| `meta_ads/scripts/audiences/get.py` | `GET /<audience_id>` — field selection, `check_error` |
| `meta_ads/scripts/audiences/create.py` | `POST /act_<id>/customaudiences` — custom audience (subtype + metadata); `--dry-run` |
| `meta_ads/scripts/audiences/create_lookalike.py` | `POST /act_<id>/customaudiences` `subtype=LOOKALIKE` — `--source-audience-id`/`--country`/`--ratio`; `--dry-run` |
| `meta_ads/scripts/audiences/add_users.py` | `POST /<audience_id>/users` — SHA-256 `payload` form param; `--dry-run`, `--yes` |
| `meta_ads/scripts/audiences/remove_users.py` | `DELETE /<audience_id>/users` — same `payload` as form/query param (not JSON body); `--dry-run`, `--yes` |
| `meta_ads/scripts/audiences/delete.py` | `DELETE /<audience_id>` — `--dry-run`, `--yes` |
| `meta_ads/scripts/audiences/_users.py` | shared helper: normalize+SHA-256 hashing, `payload` builder, identifier loading |
| `tests/meta_ads/scripts/test_audiences_list.py` | audiences/list tests |
| `tests/meta_ads/scripts/test_audiences_get.py` | audiences/get tests |
| `tests/meta_ads/scripts/test_audiences_create.py` | audiences/create tests |
| `tests/meta_ads/scripts/test_audiences_create_lookalike.py` | audiences/create_lookalike tests |
| `tests/meta_ads/scripts/test_audiences_users_helper.py` | hashing + payload-builder unit tests |
| `tests/meta_ads/scripts/test_audiences_add_users.py` | add_users tests (hashing, dry-run, gating) |
| `tests/meta_ads/scripts/test_audiences_remove_users.py` | remove_users tests (DELETE+payload-form, gating) |
| `tests/meta_ads/scripts/test_audiences_delete.py` | delete tests (dry-run, gating) |
| `skills/meta-ads-audiences/SKILL.md` | audiences cluster skill |
| `CHANGELOG.md` | version bump + M3 entry (modify) |

---

## Task 1: `audiences/list.py` and `audiences/get.py` (reads)

The two read scripts, following the M1 read templates exactly: `list.py` pages an account's custom audiences (`GET /act_<id>/customaudiences`) with `--account-id` (required, normalized via `account_path`) and field selection; `get.py` reads one audience node and `check_error`s the body.

**Files:**
- Create: `meta_ads/scripts/audiences/__init__.py`
- Create: `meta_ads/scripts/audiences/list.py`
- Create: `meta_ads/scripts/audiences/get.py`
- Create: `tests/meta_ads/scripts/test_audiences_list.py`
- Create: `tests/meta_ads/scripts/test_audiences_get.py`

- [ ] **Step 1: Create the audiences package marker.**

```bash
mkdir -p meta_ads/scripts/audiences
touch meta_ads/scripts/audiences/__init__.py
```

- [ ] **Step 2: Write failing tests.** Write `tests/meta_ads/scripts/test_audiences_list.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from meta_ads.scripts.audiences import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.audiences.list.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.audiences.list.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_audiences_list_normalizes_account_and_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [
                {
                    "id": "aud1",
                    "name": "Newsletter buyers",
                    "subtype": "CUSTOM",
                    "approximate_count_lower_bound": 1000,
                    "operation_status": {"code": 200, "description": "Normal"},
                }
            ]
        )
        with patch.object(
            sys, "argv", ["list.py", "--account-id", "123", "--output", "json"]
        ):
            assert listcmd.main() == 0
        args, kwargs = client.paginate.call_args
        assert args[0] == "act_123/customaudiences"
        params = kwargs.get("params") or args[1]
        assert "name" in params["fields"]
        assert kwargs["limit"] == 50
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "aud1"
    assert parsed[0]["subtype"] == "CUSTOM"


def test_audiences_list_passes_limit(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(
            sys, "argv", ["list.py", "--account-id", "act_123", "--limit", "5"]
        ):
            assert listcmd.main() == 0
        args, kwargs = client.paginate.call_args
        assert args[0] == "act_123/customaudiences"
        assert kwargs["limit"] == 5
```

Write `tests/meta_ads/scripts/test_audiences_get.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.audiences import get as getcmd
from meta_ads.utils.client import MetaAPIError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.audiences.get.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.audiences.get.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_audience_get_by_id(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "id": "aud1",
            "name": "Newsletter buyers",
            "subtype": "CUSTOM",
            "approximate_count_lower_bound": 1000,
        }
        with patch.object(
            sys, "argv", ["get.py", "--id", "aud1", "--output", "json"]
        ):
            assert getcmd.main() == 0
        args, kwargs = client.get.call_args
        assert args[0] == "aud1"
        assert "subtype" in kwargs["params"]["fields"]
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "aud1"
    assert parsed["name"] == "Newsletter buyers"


def test_audience_get_surfaces_api_error(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "error": {"message": "bad", "code": 100, "fbtrace_id": "Z"}
        }
        with (
            patch.object(sys, "argv", ["get.py", "--id", "aud1"]),
            pytest.raises(MetaAPIError),
        ):
            getcmd.main()
```

- [ ] **Step 3: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_audiences_list.py tests/meta_ads/scripts/test_audiences_get.py -v
```
Expected: `ModuleNotFoundError: No module named 'meta_ads.scripts.audiences.list'`.

- [ ] **Step 4: Implement `meta_ads/scripts/audiences/list.py`.** Complete code:

```python
"""List custom audiences under an ad account.

GET /act_<id>/customaudiences with field selection and cursor pagination capped
by --limit. Flattens audience nodes into flat rows for table output.
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
    "id,name,subtype,description,approximate_count_lower_bound,"
    "approximate_count_upper_bound,operation_status,delivery_status,"
    "time_created,time_updated"
)


def _flatten(node: dict) -> dict:
    op = node.get("operation_status") or {}
    return {
        "id": node.get("id"),
        "name": node.get("name"),
        "subtype": node.get("subtype"),
        "count_lower": node.get("approximate_count_lower_bound"),
        "count_upper": node.get("approximate_count_upper_bound"),
        "operation_status": op.get("description"),
        "time_updated": node.get("time_updated"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List custom audiences under an ad account.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument("--fields", default=_FIELDS)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    path = f"{account_path(args.account_id)}/customaudiences"
    params = {"fields": args.fields}
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        rows = [_flatten(n) for n in client.paginate(path, params=params, limit=args.limit)]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Implement `meta_ads/scripts/audiences/get.py`.** Complete code:

```python
"""Get a single custom audience node by --id."""

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
    "id,name,subtype,description,rule,retention_days,"
    "approximate_count_lower_bound,approximate_count_upper_bound,"
    "operation_status,delivery_status,data_source,lookalike_spec,"
    "time_created,time_updated"
)


def _flatten(node: dict) -> dict:
    op = node.get("operation_status") or {}
    return {
        "id": node.get("id"),
        "name": node.get("name"),
        "subtype": node.get("subtype"),
        "description": node.get("description"),
        "retention_days": node.get("retention_days"),
        "count_lower": node.get("approximate_count_lower_bound"),
        "count_upper": node.get("approximate_count_upper_bound"),
        "operation_status": op.get("description"),
        "time_updated": node.get("time_updated"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get a custom audience by id.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Custom audience id")
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
uv run pytest tests/meta_ads/scripts/test_audiences_list.py tests/meta_ads/scripts/test_audiences_get.py -v
uv run ruff check meta_ads/scripts/audiences/ tests/meta_ads/scripts/test_audiences_list.py tests/meta_ads/scripts/test_audiences_get.py
uv run ruff format meta_ads/scripts/audiences/ tests/meta_ads/scripts/test_audiences_list.py tests/meta_ads/scripts/test_audiences_get.py
git add meta_ads/scripts/audiences/__init__.py meta_ads/scripts/audiences/list.py meta_ads/scripts/audiences/get.py tests/meta_ads/scripts/test_audiences_list.py tests/meta_ads/scripts/test_audiences_get.py
git commit -m "feat(meta-ads): audiences/list.py and audiences/get.py"
```

---

## Task 2: `audiences/create.py`

`POST /act_<id>/customaudiences`. Builds a custom-audience create body from `--name`, `--subtype` (default `CUSTOM`), `--description`, `--customer-file-source` (required by Graph for `CUSTOM` customer-file audiences; default `USER_PROVIDED_ONLY`), and `--retention-days`. This script only *creates the audience container*; populating it is `add_users` (Task 5). `--dry-run` prints the Graph request (node + form data) and exits 0. Not `--yes`-gated (creating an empty audience is low-risk; membership writes are the gated ops, per spec §4).

**Files:**
- Create: `meta_ads/scripts/audiences/create.py`
- Create: `tests/meta_ads/scripts/test_audiences_create.py`

- [ ] **Step 1: Write failing test.** Write `tests/meta_ads/scripts/test_audiences_create.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.audiences import create as createcmd
from meta_ads.utils.client import MetaAPIError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.audiences.create.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.audiences.create.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_create_dry_run_prints_request_and_skips_post(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "create.py",
                "--account-id",
                "123",
                "--name",
                "VIP buyers",
                "--description",
                "Top spenders",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["path"] == "act_123/customaudiences"
    assert parsed["data"]["name"] == "VIP buyers"
    assert parsed["data"]["subtype"] == "CUSTOM"
    assert parsed["data"]["customer_file_source"] == "USER_PROVIDED_ONLY"


def test_create_posts_form_data(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "aud9"}
        with patch.object(
            sys,
            "argv",
            ["create.py", "--account-id", "123", "--name", "VIP buyers"],
        ):
            assert createcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "act_123/customaudiences"
        data = kwargs.get("data") or args[1]
        assert data["name"] == "VIP buyers"
        assert data["subtype"] == "CUSTOM"


def test_create_surfaces_api_error(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {
            "error": {"message": "dup", "code": 2650, "fbtrace_id": "Z"}
        }
        with (
            patch.object(
                sys, "argv", ["create.py", "--account-id", "123", "--name", "X"]
            ),
            pytest.raises(MetaAPIError),
        ):
            createcmd.main()
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_audiences_create.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `meta_ads/scripts/audiences/create.py`.** Complete code:

```python
"""Create a custom audience container under an ad account.

POST /act_<id>/customaudiences. Creates the (empty) audience; populate it with
audiences/add_users. --dry-run prints the Graph request (node + form data) and
skips the POST. Not --yes-gated: creating an empty audience is low-risk; the
membership writes (add_users/remove_users) and delete are the gated ops.
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
from meta_ads.utils.client import MetaClient, account_path, check_error


def _build_data(args: argparse.Namespace) -> dict:
    data: dict[str, object] = {
        "name": args.name,
        "subtype": args.subtype,
    }
    if args.description:
        data["description"] = args.description
    if args.retention_days is not None:
        data["retention_days"] = args.retention_days
    # Graph requires customer_file_source for customer-file (CUSTOM) audiences.
    if args.subtype == "CUSTOM":
        data["customer_file_source"] = args.customer_file_source
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a custom audience.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument("--name", required=True, help="Audience name")
    parser.add_argument(
        "--subtype",
        default="CUSTOM",
        help="Audience subtype (default CUSTOM; LOOKALIKE has its own script)",
    )
    parser.add_argument("--description", help="Audience description")
    parser.add_argument(
        "--retention-days",
        dest="retention_days",
        type=int,
        help="Membership retention in days",
    )
    parser.add_argument(
        "--customer-file-source",
        dest="customer_file_source",
        default="USER_PROVIDED_ONLY",
        choices=(
            "USER_PROVIDED_ONLY",
            "PARTNER_PROVIDED_ONLY",
            "BOTH_USER_AND_PARTNER_PROVIDED",
        ),
        help="Source of identifiers for CUSTOM audiences (Graph-required)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    path = f"{account_path(args.account_id)}/customaudiences"
    data = _build_data(args)

    if args.dry_run:
        print(format_output({"method": "POST", "path": path, "data": data}, args.output))
        return 0

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.post(path, data=data)

    check_error(result)
    print(format_output({"id": result.get("id"), "name": args.name}, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/meta_ads/scripts/test_audiences_create.py -v
uv run ruff check meta_ads/scripts/audiences/create.py tests/meta_ads/scripts/test_audiences_create.py
uv run ruff format meta_ads/scripts/audiences/create.py tests/meta_ads/scripts/test_audiences_create.py
git add meta_ads/scripts/audiences/create.py tests/meta_ads/scripts/test_audiences_create.py
git commit -m "feat(meta-ads): audiences/create.py with --dry-run"
```

---

## Task 3: `audiences/create_lookalike.py`

`POST /act_<id>/customaudiences` with `subtype=LOOKALIKE`. Builds the Graph `lookalike_spec` JSON object from `--source-audience-id`, `--country`, and `--ratio` (the seed audience's similarity fraction, e.g. `0.01` = top 1%). `--dry-run` prints the request; not `--yes`-gated (no membership/identifier write; this just defines a derived audience).

**Files:**
- Create: `meta_ads/scripts/audiences/create_lookalike.py`
- Create: `tests/meta_ads/scripts/test_audiences_create_lookalike.py`

- [ ] **Step 1: Write failing test.** Write `tests/meta_ads/scripts/test_audiences_create_lookalike.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.audiences import create_lookalike as lookcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(
        patch("meta_ads.scripts.audiences.create_lookalike.load_config")
    )
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.audiences.create_lookalike.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_lookalike_dry_run_builds_spec(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "create_lookalike.py",
                "--account-id",
                "123",
                "--name",
                "LAL 1% US",
                "--source-audience-id",
                "aud1",
                "--country",
                "US",
                "--ratio",
                "0.01",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert lookcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["path"] == "act_123/customaudiences"
    assert parsed["data"]["subtype"] == "LOOKALIKE"
    assert parsed["data"]["origin_audience_id"] == "aud1"
    spec = json.loads(parsed["data"]["lookalike_spec"])
    assert spec["country"] == "US"
    assert spec["ratio"] == 0.01


def test_lookalike_posts_form_data(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "lal9"}
        with patch.object(
            sys,
            "argv",
            [
                "create_lookalike.py",
                "--account-id",
                "123",
                "--name",
                "LAL",
                "--source-audience-id",
                "aud1",
                "--country",
                "US",
                "--ratio",
                "0.03",
            ],
        ):
            assert lookcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "act_123/customaudiences"
        data = kwargs.get("data") or args[1]
        assert data["subtype"] == "LOOKALIKE"
        spec = json.loads(data["lookalike_spec"])
        assert spec["ratio"] == 0.03


def test_lookalike_ratio_out_of_range_errors(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with (
            patch.object(
                sys,
                "argv",
                [
                    "create_lookalike.py",
                    "--account-id",
                    "123",
                    "--name",
                    "LAL",
                    "--source-audience-id",
                    "aud1",
                    "--country",
                    "US",
                    "--ratio",
                    "0.5",
                ],
            ),
            pytest.raises(SystemExit),
        ):
            lookcmd.main()
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_audiences_create_lookalike.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `meta_ads/scripts/audiences/create_lookalike.py`.** Complete code:

```python
"""Create a lookalike audience from a seed (source) audience.

POST /act_<id>/customaudiences with subtype=LOOKALIKE. The Graph lookalike_spec
JSON carries the target country and the similarity ratio (e.g. 0.01 = closest
1%). --dry-run prints the request; not --yes-gated (no identifier/membership
write — this only defines a derived audience).
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
from meta_ads.utils.client import MetaClient, account_path, check_error


def _build_data(args: argparse.Namespace) -> dict:
    spec = {"country": args.country, "ratio": args.ratio, "type": "similarity"}
    return {
        "name": args.name,
        "subtype": "LOOKALIKE",
        "origin_audience_id": args.source_audience_id,
        "lookalike_spec": json.dumps(spec),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a lookalike audience.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument("--name", required=True, help="Lookalike audience name")
    parser.add_argument(
        "--source-audience-id",
        dest="source_audience_id",
        required=True,
        help="Seed (origin) custom-audience id",
    )
    parser.add_argument(
        "--country", required=True, help="Target country code (e.g. US, SE)"
    )
    parser.add_argument(
        "--ratio",
        type=float,
        required=True,
        help="Similarity ratio in (0, 0.2] (e.g. 0.01 = closest 1%%)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if not 0 < args.ratio <= 0.2:
        parser.error("--ratio must be in the range (0, 0.2]")

    path = f"{account_path(args.account_id)}/customaudiences"
    data = _build_data(args)

    if args.dry_run:
        print(format_output({"method": "POST", "path": path, "data": data}, args.output))
        return 0

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.post(path, data=data)

    check_error(result)
    print(format_output({"id": result.get("id"), "name": args.name}, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/meta_ads/scripts/test_audiences_create_lookalike.py -v
uv run ruff check meta_ads/scripts/audiences/create_lookalike.py tests/meta_ads/scripts/test_audiences_create_lookalike.py
uv run ruff format meta_ads/scripts/audiences/create_lookalike.py tests/meta_ads/scripts/test_audiences_create_lookalike.py
git add meta_ads/scripts/audiences/create_lookalike.py tests/meta_ads/scripts/test_audiences_create_lookalike.py
git commit -m "feat(meta-ads): audiences/create_lookalike.py (subtype=LOOKALIKE) with --dry-run"
```

---

## Task 4: `audiences/_users.py` — shared hashing + payload helper

Both `add_users` and `remove_users` normalize identifiers, SHA-256-hash them, and build the Graph `payload` `{schema, data}` object. Factor this into one helper so both scripts (and their tests) share the exact same hashing and `payload` shape.

**Files:**
- Create: `meta_ads/scripts/audiences/_users.py`
- Create: `tests/meta_ads/scripts/test_audiences_users_helper.py`

- [ ] **Step 1: Write failing test.** Write `tests/meta_ads/scripts/test_audiences_users_helper.py`:

```python
import hashlib
import json

import pytest

from meta_ads.scripts.audiences import _users


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def test_normalize_lowercases_and_trims():
    assert _users.normalize("  Ada@B.COM  ") == "ada@b.com"


def test_hash_value_normalizes_then_sha256():
    assert _users.hash_value("  Ada@B.COM ") == _sha("ada@b.com")


def test_build_payload_email_schema():
    payload = _users.build_payload("EMAIL_SHA256", ["a@b.com", "c@d.com"])
    assert payload["schema"] == "EMAIL_SHA256"
    assert payload["data"] == [[_sha("a@b.com")], [_sha("c@d.com")]]


def test_build_payload_phone_schema():
    payload = _users.build_payload("PHONE_SHA256", ["+1 555 000"])
    # phone normalized to lowercase+trim only (digits left intact for the hash)
    assert payload["data"] == [[_sha("+1 555 000".strip().lower())]]


def test_payload_param_is_json_string():
    param = _users.payload_param("EMAIL_SHA256", ["a@b.com"])
    decoded = json.loads(param)
    assert decoded["schema"] == "EMAIL_SHA256"
    assert decoded["data"] == [[_sha("a@b.com")]]


def test_schema_for_resolves_email_and_phone():
    assert _users.schema_for("email") == "EMAIL_SHA256"
    assert _users.schema_for("phone") == "PHONE_SHA256"


def test_schema_for_rejects_unknown():
    with pytest.raises(ValueError):
        _users.schema_for("zip")


def test_load_identifiers_from_args_inline():
    args = type("A", (), {"value": ["a@b.com", "c@d.com"], "value_file": None})()
    assert _users.load_identifiers(args) == ["a@b.com", "c@d.com"]


def test_load_identifiers_from_file(tmp_path):
    f = tmp_path / "ids.txt"
    f.write_text("a@b.com\n\nc@d.com\n")
    args = type("A", (), {"value": None, "value_file": str(f)})()
    assert _users.load_identifiers(args) == ["a@b.com", "c@d.com"]


def test_load_identifiers_requires_some():
    args = type("A", (), {"value": None, "value_file": None})()
    with pytest.raises(ValueError):
        _users.load_identifiers(args)
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_audiences_users_helper.py -v
```
Expected: `ModuleNotFoundError: No module named 'meta_ads.scripts.audiences._users'`.

- [ ] **Step 3: Implement `meta_ads/scripts/audiences/_users.py`.** Complete code:

```python
"""Shared helpers for audience membership writes (add_users / remove_users).

Meta's customer-file matching requires identifiers to be normalized (trimmed +
lowercased) and SHA-256-hashed before transmission. Both membership scripts send
a Graph ``payload`` object ``{"schema": <SCHEMA>, "data": [[<hash>], ...]}``
JSON-encoded as the ``payload`` form/query param.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

# Map the user-facing identifier kind to the Graph schema name.
_SCHEMAS = {
    "email": "EMAIL_SHA256",
    "phone": "PHONE_SHA256",
}


def schema_for(kind: str) -> str:
    """Return the Graph schema name for an identifier kind ('email'/'phone')."""
    try:
        return _SCHEMAS[kind]
    except KeyError:
        raise ValueError(f"unsupported identifier kind: {kind!r}") from None


def normalize(value: str) -> str:
    """Trim surrounding whitespace and lowercase (Meta's required pre-hash form)."""
    return value.strip().lower()


def hash_value(value: str) -> str:
    """Normalize then SHA-256-hash an identifier, returning the hex digest."""
    return hashlib.sha256(normalize(value).encode("utf-8")).hexdigest()


def build_payload(schema: str, values: list[str]) -> dict:
    """Build the Graph payload object: schema + one single-element row per hash."""
    return {"schema": schema, "data": [[hash_value(v)] for v in values]}


def payload_param(schema: str, values: list[str]) -> str:
    """Return the JSON-encoded payload string for the Graph ``payload`` param."""
    return json.dumps(build_payload(schema, values))


def load_identifiers(args: argparse.Namespace) -> list[str]:
    """Collect identifiers from --value (repeatable) or --value-file (one per line).

    Raises ValueError when neither is given or the result is empty.
    """
    if args.value:
        values = list(args.value)
    elif args.value_file:
        text = Path(args.value_file).read_text(encoding="utf-8")
        values = [line.strip() for line in text.splitlines() if line.strip()]
    else:
        raise ValueError("provide identifiers via --value or --value-file")
    if not values:
        raise ValueError("no identifiers found")
    return values
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/meta_ads/scripts/test_audiences_users_helper.py -v
uv run ruff check meta_ads/scripts/audiences/_users.py tests/meta_ads/scripts/test_audiences_users_helper.py
uv run ruff format meta_ads/scripts/audiences/_users.py tests/meta_ads/scripts/test_audiences_users_helper.py
git add meta_ads/scripts/audiences/_users.py tests/meta_ads/scripts/test_audiences_users_helper.py
git commit -m "feat(meta-ads): audiences/_users.py (SHA-256 hashing + payload builder)"
```

---

## Task 5: `audiences/add_users.py`

`POST /<audience_id>/users`. Loads identifiers (`--value` repeatable or `--value-file`), resolves the schema from `--kind` (`email`/`phone`), hashes them via the Task-4 helper, and sends the `payload` JSON in the POST **form body**. `--dry-run` prints the request (and confirms hashing — no raw identifiers in the output). `--yes`-gated: live execution requires `--yes` (membership writes are high-stakes, spec §4); `--dry-run` works without `--yes`.

**Files:**
- Create: `meta_ads/scripts/audiences/add_users.py`
- Create: `tests/meta_ads/scripts/test_audiences_add_users.py`

- [ ] **Step 1: Write failing test.** Write `tests/meta_ads/scripts/test_audiences_add_users.py`:

```python
import hashlib
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.audiences import add_users as addcmd


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(
        patch("meta_ads.scripts.audiences.add_users.load_config")
    )
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.audiences.add_users.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_add_users_dry_run_hashes_and_skips_post(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "add_users.py",
                "--id",
                "aud1",
                "--kind",
                "email",
                "--value",
                "Ada@B.com",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert addcmd.main() == 0
        assert client.post.call_count == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["method"] == "POST"
    assert parsed["path"] == "aud1/users"
    payload = json.loads(parsed["data"]["payload"])
    assert payload["schema"] == "EMAIL_SHA256"
    assert payload["data"] == [[_sha("ada@b.com")]]
    # raw identifier must not leak into the printed request
    assert "Ada@B.com" not in out


def test_add_users_posts_payload_form(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"num_received": 1, "num_invalid_entries": 0}
        with patch.object(
            sys,
            "argv",
            [
                "add_users.py",
                "--id",
                "aud1",
                "--kind",
                "email",
                "--value",
                "a@b.com",
                "--yes",
            ],
        ):
            assert addcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "aud1/users"
        data = kwargs.get("data") or args[1]
        payload = json.loads(data["payload"])
        assert payload["schema"] == "EMAIL_SHA256"
        assert payload["data"] == [[_sha("a@b.com")]]


def test_add_users_requires_yes_for_live(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with (
            patch.object(
                sys,
                "argv",
                ["add_users.py", "--id", "aud1", "--kind", "email", "--value", "a@b.com"],
            ),
            pytest.raises(SystemExit),
        ):
            addcmd.main()
        assert client.post.call_count == 0
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_audiences_add_users.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `meta_ads/scripts/audiences/add_users.py`.** Complete code:

```python
"""Add (hashed) users to a custom audience.

POST /<audience_id>/users with the Graph ``payload`` form param carrying
SHA-256-hashed identifiers ({schema, data}). Identifiers come from --value
(repeatable) or --value-file (one per line) and are normalized + hashed before
transmission (raw values never leave the process). --dry-run prints the request
(hashed) and skips the POST. High-stakes: --yes is required for live execution.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from meta_ads.scripts.audiences._users import (
    load_identifiers,
    payload_param,
    schema_for,
)
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, check_error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Add hashed users to a custom audience.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Custom audience id")
    parser.add_argument(
        "--kind",
        default="email",
        choices=("email", "phone"),
        help="Identifier kind (selects the SHA-256 schema)",
    )
    parser.add_argument(
        "--value",
        action="append",
        help="An identifier to add (repeatable)",
    )
    parser.add_argument(
        "--value-file",
        dest="value_file",
        help="File with one identifier per line",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    try:
        identifiers = load_identifiers(args)
    except ValueError as exc:
        parser.error(str(exc))

    schema = schema_for(args.kind)
    payload = payload_param(schema, identifiers)
    path = f"{args.id}/users"
    data = {"payload": payload}

    if args.dry_run:
        print(
            format_output(
                {"method": "POST", "path": path, "data": data, "count": len(identifiers)},
                args.output,
            )
        )
        return 0

    if not args.yes:
        parser.error("--yes is required to add users to an audience; aborting")

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.post(path, data=data)

    check_error(result)
    print(format_output(result, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/meta_ads/scripts/test_audiences_add_users.py -v
uv run ruff check meta_ads/scripts/audiences/add_users.py tests/meta_ads/scripts/test_audiences_add_users.py
uv run ruff format meta_ads/scripts/audiences/add_users.py tests/meta_ads/scripts/test_audiences_add_users.py
git add meta_ads/scripts/audiences/add_users.py tests/meta_ads/scripts/test_audiences_add_users.py
git commit -m "feat(meta-ads): audiences/add_users.py (SHA-256 payload form, --dry-run, --yes)"
```

---

## Task 6: `audiences/remove_users.py`

`DELETE /<audience_id>/users` carrying the **same `payload`** as a form/query param — **NOT a JSON body** (spec §5 M3 note). `MetaClient.delete(path, params=...)` passes params through `core.http`, so the `payload` rides as a query/form param on the DELETE. Same hashing helper, same schema selection, same `--dry-run`/`--yes` posture as `add_users`.

**Files:**
- Create: `meta_ads/scripts/audiences/remove_users.py`
- Create: `tests/meta_ads/scripts/test_audiences_remove_users.py`

- [ ] **Step 1: Write failing test.** Write `tests/meta_ads/scripts/test_audiences_remove_users.py`:

```python
import hashlib
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.audiences import remove_users as rmcmd


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(
        patch("meta_ads.scripts.audiences.remove_users.load_config")
    )
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.audiences.remove_users.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_remove_users_dry_run_hashes_and_skips_delete(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "remove_users.py",
                "--id",
                "aud1",
                "--kind",
                "email",
                "--value",
                "A@B.com",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert rmcmd.main() == 0
        assert client.delete.call_count == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["method"] == "DELETE"
    assert parsed["path"] == "aud1/users"
    # payload rides as a query/form param, not a JSON body
    payload = json.loads(parsed["params"]["payload"])
    assert payload["schema"] == "EMAIL_SHA256"
    assert payload["data"] == [[_sha("a@b.com")]]
    assert "A@B.com" not in out


def test_remove_users_deletes_with_payload_param(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.delete.return_value = {"num_received": 1}
        with patch.object(
            sys,
            "argv",
            [
                "remove_users.py",
                "--id",
                "aud1",
                "--kind",
                "email",
                "--value",
                "a@b.com",
                "--yes",
            ],
        ):
            assert rmcmd.main() == 0
        args, kwargs = client.delete.call_args
        assert args[0] == "aud1/users"
        # must use params=, NOT a json/body kwarg
        assert "json" not in kwargs
        params = kwargs.get("params") or args[1]
        payload = json.loads(params["payload"])
        assert payload["data"] == [[_sha("a@b.com")]]


def test_remove_users_requires_yes_for_live(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with (
            patch.object(
                sys,
                "argv",
                [
                    "remove_users.py",
                    "--id",
                    "aud1",
                    "--kind",
                    "email",
                    "--value",
                    "a@b.com",
                ],
            ),
            pytest.raises(SystemExit),
        ):
            rmcmd.main()
        assert client.delete.call_count == 0
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_audiences_remove_users.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `meta_ads/scripts/audiences/remove_users.py`.** Complete code:

```python
"""Remove (hashed) users from a custom audience.

DELETE /<audience_id>/users carrying the same Graph ``payload`` object as a
form/query param (NOT a JSON body — spec note). Identifiers come from --value
(repeatable) or --value-file and are normalized + SHA-256-hashed before
transmission. --dry-run prints the request (hashed) and skips the DELETE.
High-stakes: --yes is required for live execution.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import sys

from core.config import load_config
from meta_ads.scripts.audiences._users import (
    load_identifiers,
    payload_param,
    schema_for,
)
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, check_error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Remove hashed users from a custom audience."
    )
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Custom audience id")
    parser.add_argument(
        "--kind",
        default="email",
        choices=("email", "phone"),
        help="Identifier kind (selects the SHA-256 schema)",
    )
    parser.add_argument(
        "--value",
        action="append",
        help="An identifier to remove (repeatable)",
    )
    parser.add_argument(
        "--value-file",
        dest="value_file",
        help="File with one identifier per line",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    try:
        identifiers = load_identifiers(args)
    except ValueError as exc:
        parser.error(str(exc))

    schema = schema_for(args.kind)
    payload = payload_param(schema, identifiers)
    path = f"{args.id}/users"
    params = {"payload": payload}

    if args.dry_run:
        print(
            format_output(
                {
                    "method": "DELETE",
                    "path": path,
                    "params": params,
                    "count": len(identifiers),
                },
                args.output,
            )
        )
        return 0

    if not args.yes:
        parser.error("--yes is required to remove users from an audience; aborting")

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.delete(path, params=params)

    check_error(result)
    print(format_output(result, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/meta_ads/scripts/test_audiences_remove_users.py -v
uv run ruff check meta_ads/scripts/audiences/remove_users.py tests/meta_ads/scripts/test_audiences_remove_users.py
uv run ruff format meta_ads/scripts/audiences/remove_users.py tests/meta_ads/scripts/test_audiences_remove_users.py
git add meta_ads/scripts/audiences/remove_users.py tests/meta_ads/scripts/test_audiences_remove_users.py
git commit -m "feat(meta-ads): audiences/remove_users.py (DELETE with payload form param, --yes)"
```

---

## Task 7: `audiences/delete.py`

`DELETE /<audience_id>`. Destructive: `--yes` required for live execution; `--dry-run` prints the intended deletion and exits 0 without requiring `--yes` (mirrors the `add_users`/`remove_users` posture and the Shopify `webhooks/delete.py` precedent).

**Files:**
- Create: `meta_ads/scripts/audiences/delete.py`
- Create: `tests/meta_ads/scripts/test_audiences_delete.py`

- [ ] **Step 1: Write failing test.** Write `tests/meta_ads/scripts/test_audiences_delete.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.audiences import delete as delcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.audiences.delete.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.audiences.delete.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_delete_dry_run_skips_call(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["delete.py", "--id", "aud1", "--dry-run", "--output", "json"]
        ):
            assert delcmd.main() == 0
        assert client.delete.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["method"] == "DELETE"
    assert parsed["path"] == "aud1"


def test_delete_requires_yes(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with (
            patch.object(sys, "argv", ["delete.py", "--id", "aud1"]),
            pytest.raises(SystemExit),
        ):
            delcmd.main()
        assert client.delete.call_count == 0


def test_delete_calls_with_yes(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.delete.return_value = {"success": True}
        with patch.object(sys, "argv", ["delete.py", "--id", "aud1", "--yes"]):
            assert delcmd.main() == 0
        args, _ = client.delete.call_args
        assert args[0] == "aud1"
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_audiences_delete.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `meta_ads/scripts/audiences/delete.py`.** Complete code:

```python
"""Delete a custom audience.

Destructive: requires --yes to actually run the deletion. --dry-run prints the
intended deletion and exits 0 without requiring --yes.
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
from meta_ads.utils.client import MetaClient, check_error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Delete a custom audience.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Custom audience id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if args.dry_run:
        print(format_output({"method": "DELETE", "path": args.id}, args.output))
        return 0

    if not args.yes:
        parser.error("--yes is required to confirm deletion; aborting")

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.delete(args.id)

    check_error(result)
    print(format_output({"deleted": args.id, "result": result}, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/meta_ads/scripts/test_audiences_delete.py -v
uv run ruff check meta_ads/scripts/audiences/delete.py tests/meta_ads/scripts/test_audiences_delete.py
uv run ruff format meta_ads/scripts/audiences/delete.py tests/meta_ads/scripts/test_audiences_delete.py
git add meta_ads/scripts/audiences/delete.py tests/meta_ads/scripts/test_audiences_delete.py
git commit -m "feat(meta-ads): audiences/delete.py (--dry-run, --yes)"
```

---

## Task 8: Skill — `meta-ads-audiences`

**Files:**
- Create: `skills/meta-ads-audiences/SKILL.md`

Mirror the `skills/meta-ads-structure/SKILL.md` (M1) front-matter shape: a `name:` line and a single-paragraph `description:` packed with trigger phrases, then a body covering when to use, each script, and the safety posture.

- [ ] **Step 1: Write `skills/meta-ads-audiences/SKILL.md`.** Cover the full cluster: `audiences/{list,get,create,create_lookalike,add_users,remove_users,delete}`. Front-matter `description` must name triggers: "list custom audiences", "create a custom audience", "create a lookalike audience", "add users to an audience", "remove users from an audience", "upload hashed emails", "delete a custom audience", "Meta audience targeting". Body notes:
  - Every script takes `--account-id` (normalized to `act_<id>`, where applicable), `--output {table,json,markdown}`, `--api-version`, and reads honor `--limit`/pagination.
  - `create` makes an empty CUSTOM container (`--subtype`, `--description`, `--retention-days`, `--customer-file-source`); `create_lookalike` derives one from `--source-audience-id`/`--country`/`--ratio` (ratio in `(0, 0.2]`).
  - **Identifier privacy:** `add_users`/`remove_users` normalize (trim+lowercase) and **SHA-256-hash** every `--value`/`--value-file` identifier before transmission; raw identifiers never leave the process and never appear in `--dry-run` output. `--kind email|phone` selects the `EMAIL_SHA256`/`PHONE_SHA256` schema.
  - **Transport note:** `add_users` POSTs the `payload` in the form body; `remove_users` issues a **DELETE with the `payload` as a query/form param** (not a JSON body).
  - **Safety posture:** every mutation supports `--dry-run` (prints the Graph request and exits 0). `add_users`, `remove_users`, and `delete` are **`--yes`-gated** (live execution aborts via `parser.error` before any network call when `--yes` is missing). `create`/`create_lookalike` are not gated (no identifier/membership write).
  - Defer Conversions API / Pixel event ingestion and catalog/commerce audiences to direct API use (out of domain scope, spec §2).

- [ ] **Step 2: Commit.**

```bash
git add skills/meta-ads-audiences/SKILL.md
git commit -m "docs(meta-ads): meta-ads-audiences skill"
```

---

## Task 9: Full sweep, CHANGELOG, smoke

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Full suite + ruff (with the meta-ads extra installed).**

```bash
uv sync --extra dev --extra shopify --extra webhooks --extra klaviyo --extra meta-ads
uv run pytest tests/ --ignore=tests/shopify/test_whoami_integration.py -v
uv run ruff check .
uv run ruff format --check .
```
Expected: all green; the new `tests/meta_ads/scripts/test_audiences_*.py` suite is collected and passes; existing Shopify/Klaviyo/Meta-M1 tests unaffected.

- [ ] **Step 2: Smoke each audiences script's `--help` and the dry-run paths.**

```bash
uv run meta_ads/scripts/audiences/list.py --help
uv run meta_ads/scripts/audiences/get.py --help
uv run meta_ads/scripts/audiences/create.py --help
uv run meta_ads/scripts/audiences/create_lookalike.py --help
uv run meta_ads/scripts/audiences/add_users.py --help
uv run meta_ads/scripts/audiences/remove_users.py --help
uv run meta_ads/scripts/audiences/delete.py --help
# dry-runs (no token needed; should print the request and exit 0)
uv run meta_ads/scripts/audiences/add_users.py --id aud1 --kind email --value a@b.com --dry-run --output json
uv run meta_ads/scripts/audiences/remove_users.py --id aud1 --kind email --value a@b.com --dry-run --output json
uv run meta_ads/scripts/audiences/delete.py --id aud1 --dry-run --output json
```
Expected: help text prints for every script; each dry-run prints a JSON request (hashed payload for the user ops) and exits 0. Confirm raw `a@b.com` does NOT appear in the add/remove dry-run JSON (only its SHA-256 hash).

- [ ] **Step 3: Update `CHANGELOG.md`.** Add a new version heading bumping the current `0.9.0` (M1) minor line to `## [0.10.0] — 2026-05-29`, with an `### Added` entry noting: the Meta Ads audiences cluster (`audiences/{list,get,create,create_lookalike,add_users,remove_users,delete}`), the SHA-256 identifier hashing helper (`audiences/_users.py`), and the `meta-ads-audiences` skill. Note the conventions in a `### Conventions` subsection: every mutation supports `--dry-run`; `add_users`/`remove_users`/`delete` are `--yes`-gated; `add_users` POSTs the `payload` form param while `remove_users` issues a DELETE carrying `payload` as a query/form param; `create`/`create_lookalike` are not gated. Add a `### Milestone` note: the Meta Ads domain is now complete across reads+insights (M1), structure CRUD (M2), and audiences (M3); **the domain git tag is created by the controller after this plan lands — do not create it in these steps.**

- [ ] **Step 4: Commit.**

```bash
git add CHANGELOG.md
git commit -m "docs(meta-ads): CHANGELOG for Meta Ads audiences (M3)"
```

---

## Definition of Done

(Scoped to M3, per spec §11/§12.)

- [ ] All seven audiences scripts exist and run (`--help` works): `audiences/{list,get,create,create_lookalike,add_users,remove_users,delete}`, plus the shared `audiences/_users.py` helper.
- [ ] Reads (`list`/`get`) use `--account-id` (normalized via `account_path` for `list`), `--fields` selection, `--limit`/pagination (`list`), `check_error`, and `--output {table,json,markdown}`.
- [ ] `create` builds a CUSTOM container (`--name`, `--subtype`, `--description`, `--retention-days`, `--customer-file-source`); `create_lookalike` POSTs `subtype=LOOKALIKE` with a `lookalike_spec` from `--source-audience-id`/`--country`/`--ratio` (ratio validated to `(0, 0.2]`). Both support `--dry-run`; neither is `--yes`-gated.
- [ ] `add_users`/`remove_users` normalize (trim+lowercase) and **SHA-256-hash** identifiers from `--value`/`--value-file`, select the `EMAIL_SHA256`/`PHONE_SHA256` schema via `--kind`, and build the `payload` `{schema, data}` object. **`add_users` sends `payload` in the POST form body; `remove_users` issues `DELETE /<id>/users` with `payload` as a query/form param (not a JSON body).** Unit tests assert the hashing shape (lowercased input hashed, one single-element row per hash) and that raw identifiers never appear in `--dry-run` output.
- [ ] `add_users`, `remove_users`, and `delete` are `--yes`-gated: live execution aborts via `parser.error` before any network call when `--yes` is missing; `--dry-run` works without `--yes` for all three.
- [ ] Per-script unit tests green, mocking `MetaClient` (no live calls); any integration tests gated by `META_INTEGRATION_TESTS=1` and skipped by default. No new `MetaClient`/`core/` changes (M3 reuses M1's `post`/`delete`).
- [ ] `meta-ads-audiences` skill present, covering the cluster, the SHA-256 hashing/privacy note, the `add_users` vs `remove_users` transport difference, and the `--dry-run`/`--yes` posture.
- [ ] Full `uv run pytest tests/` green; `ruff check .` and `ruff format --check .` clean.
- [ ] `CHANGELOG.md` bumped to `0.10.0` with the M3 entry and the domain-complete milestone note. The domain git tag is created by the controller after this plan lands (not in these steps).
