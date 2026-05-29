# Plan K3: Klaviyo Flows + Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the Klaviyo reporting cluster — flows (`list`/`get`/`update_status`), metrics (`list`/`get`/`aggregate`), events (`list`/`create`), and reports (`campaign`/`flow`) — as `uv run klaviyo/scripts/<cluster>/<op>.py` scripts, with `--dry-run` on every mutation, `--yes` gating the flow status change, and POST-based aggregate/report queries whose JSON:API request-body shape is exercised by unit tests.

**Architecture:** Every script reuses the Plan K1 foundation: `KlaviyoClient` (JSON:API over `core.http.HttpClient`; Klaviyo-API-Key auth; dated `revision` header; `check_errors` on `errors[]`) and `klaviyo/utils/cli.py` (`add_common_flags`, `add_klaviyo_flags`, `configure_logging_from_args`, `format_output`). Reads (`flows/list`, `metrics/list`, `events/list`) flatten JSON:API resources into flat rows via `paginate`; gets fetch a single resource (optionally with related sub-resources). Mutations and POST-query scripts build a JSON:API body, print it under `--dry-run` and return 0, otherwise call the API and `check_errors`. The aggregate (`POST /metric-aggregates`) and reporting (`POST /campaign-values-reports`, `POST /flow-values-reports`) scripts are read-style queries that happen to use POST with a structured body; their body shape is the load-bearing test surface.

**Tech Stack:** `httpx>=0.27`, `pyyaml>=6`, `pydantic>=2.7` (the `klaviyo` extra populated in Plan K1). Tests use `pytest` with `unittest.mock.patch`/`monkeypatch`. No vendor SDK, no MCP.

**Spec reference:** `docs/superpowers/specs/2026-05-29-klaviyo-domain-design.md` §5 K3 (reporting script inventory: `flows/{list,get,update_status}`, `metrics/{list,get,aggregate}`, `events/{list,create}`, `reports/{campaign,flow}`), §4 (conventions — `--dry-run`, `--yes` gates flow `update_status`, `--limit`/pagination, JSON:API flattening), §6 (data flow), §7 (error handling), §8 (testing: mock `KlaviyoClient`, assert request body for POST queries), §10 (`klaviyo-flows`/`klaviyo-metrics` skills), §11 (implementation split — Plan K3), §12 (domain-level definition of done — tag when K3 lands, CHANGELOG).

**Depends on:** Plan K1 (`klaviyo/utils/client.py` with `KlaviyoClient`/`KlaviyoAPIError`/`check_errors`/`paginate`; `klaviyo/utils/cli.py` with the common + klaviyo flags; `klaviyo` extra installable; config + CI wiring). Plan K2 (sending) is independent of K3 and is not required. No `core/` changes.

---

## File Structure

| Path | Responsibility |
|---|---|
| `klaviyo/scripts/flows/__init__.py` | empty package marker |
| `klaviyo/scripts/flows/list.py` | `GET /flows` — flattened rows, pagination |
| `klaviyo/scripts/flows/get.py` | `GET /flows/{id}` (+ flow-actions with `--with-actions`) |
| `klaviyo/scripts/flows/update_status.py` | `PATCH /flows/{id}` status; activate/deactivate; `--dry-run`, `--yes` |
| `klaviyo/scripts/metrics/__init__.py` | empty package marker |
| `klaviyo/scripts/metrics/list.py` | `GET /metrics` — flattened rows, pagination |
| `klaviyo/scripts/metrics/get.py` | `GET /metrics/{id}` |
| `klaviyo/scripts/metrics/aggregate.py` | `POST /metric-aggregates` — JSON:API query body, `--dry-run` |
| `klaviyo/scripts/events/__init__.py` | empty package marker |
| `klaviyo/scripts/events/list.py` | `GET /events` — filters metric/profile/time, pagination |
| `klaviyo/scripts/events/create.py` | `POST /events` — track an event, `--dry-run` |
| `klaviyo/scripts/reports/__init__.py` | empty package marker |
| `klaviyo/scripts/reports/campaign.py` | `POST /campaign-values-reports` — JSON:API query body, `--dry-run` |
| `klaviyo/scripts/reports/flow.py` | `POST /flow-values-reports` — JSON:API query body, `--dry-run` |
| `tests/klaviyo/scripts/test_flows_list.py` | flows/list tests |
| `tests/klaviyo/scripts/test_flows_get.py` | flows/get tests |
| `tests/klaviyo/scripts/test_flows_update_status.py` | flows/update_status gated-mutation tests |
| `tests/klaviyo/scripts/test_metrics_list.py` | metrics/list tests |
| `tests/klaviyo/scripts/test_metrics_get.py` | metrics/get tests |
| `tests/klaviyo/scripts/test_metrics_aggregate.py` | metrics/aggregate body-shape tests |
| `tests/klaviyo/scripts/test_events_list.py` | events/list tests |
| `tests/klaviyo/scripts/test_events_create.py` | events/create body-shape tests |
| `tests/klaviyo/scripts/test_reports_campaign.py` | reports/campaign body-shape tests |
| `tests/klaviyo/scripts/test_reports_flow.py` | reports/flow body-shape tests |
| `skills/klaviyo-flows/SKILL.md` | flows cluster skill (incl. events) |
| `skills/klaviyo-metrics/SKILL.md` | metrics + reports cluster skill |
| `CHANGELOG.md` | K3 / domain-complete entry (modify) |

---

## Task 1: `flows/list.py` (reference read script)

First K3 script — the template for the reporting reads: flatten JSON:API resources into flat rows and page via the client's `paginate` capped by `--limit`.

**Files:**
- Create: `klaviyo/scripts/flows/__init__.py`
- Create: `klaviyo/scripts/flows/list.py`
- Create: `tests/klaviyo/scripts/test_flows_list.py`

- [ ] **Step 1: Create the package marker.**

```bash
mkdir -p klaviyo/scripts/flows tests/klaviyo/scripts
touch klaviyo/scripts/flows/__init__.py
```

- [ ] **Step 2: Write failing test.** Write `tests/klaviyo/scripts/test_flows_list.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.flows import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.flows.list.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.flows.list.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_flows_list_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [
                {
                    "id": "FLOW1",
                    "type": "flow",
                    "attributes": {
                        "name": "Welcome",
                        "status": "live",
                        "archived": False,
                        "trigger_type": "List",
                    },
                }
            ]
        )
        with patch.object(sys, "argv", ["list.py", "--output", "json"]):
            assert listcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "FLOW1"
    assert parsed[0]["name"] == "Welcome"
    assert parsed[0]["status"] == "live"


def test_flows_list_status_filter_builds_param(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py", "--status", "live"]):
            assert listcmd.main() == 0
        _, kwargs = client.paginate.call_args
        assert kwargs["params"]["filter"] == 'equals(status,"live")'


def test_flows_list_passes_limit(monkeypatch):
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
uv run pytest tests/klaviyo/scripts/test_flows_list.py -v
```
Expected: `ModuleNotFoundError: No module named 'klaviyo.scripts.flows.list'`.

- [ ] **Step 4: Implement `klaviyo/scripts/flows/list.py`.** Complete code:

```python
"""List Klaviyo flows.

Optional --status filter (e.g. ``live``, ``draft``, ``manual``). Flattens
JSON:API flow resources into flat rows. Honors --limit via cursor pagination.
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
        "status": attrs.get("status"),
        "archived": attrs.get("archived"),
        "trigger_type": attrs.get("trigger_type"),
        "created": attrs.get("created"),
        "updated": attrs.get("updated"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Klaviyo flows.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument(
        "--status", help="Filter by flow status (e.g. live, draft, manual)"
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    params: dict[str, object] = {}
    if args.status:
        params["filter"] = f'equals(status,"{args.status}")'

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        rows = [_flatten(r) for r in client.paginate("flows", params=params, limit=args.limit)]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run, confirm pass.**

```bash
uv run pytest tests/klaviyo/scripts/test_flows_list.py -v
```
Expected: all tests pass.

- [ ] **Step 6: Ruff + commit.**

```bash
uv run ruff check klaviyo/scripts/flows/list.py tests/klaviyo/scripts/test_flows_list.py
uv run ruff format klaviyo/scripts/flows/list.py tests/klaviyo/scripts/test_flows_list.py
git add klaviyo/scripts/flows/__init__.py klaviyo/scripts/flows/list.py tests/klaviyo/scripts/test_flows_list.py
git commit -m "feat(klaviyo): flows/list.py with status filter"
```

---

## Task 2: `flows/get.py`

`GET /flows/{id}`; with `--with-actions`, also fetch `GET /flows/{id}/flow-actions` and include flattened action rows in the output.

**Files:**
- Create: `klaviyo/scripts/flows/get.py`
- Create: `tests/klaviyo/scripts/test_flows_get.py`

- [ ] **Step 1: Write failing test.** Write `tests/klaviyo/scripts/test_flows_get.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.flows import get as getcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.flows.get.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.flows.get.KlaviyoClient"))
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
            "data": {
                "id": "FLOW1",
                "type": "flow",
                "attributes": {"name": "Welcome", "status": "live"},
            }
        }
        with patch.object(sys, "argv", ["get.py", "--id", "FLOW1", "--output", "json"]):
            assert getcmd.main() == 0
        client.get.assert_called_once_with("flows/FLOW1")
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "FLOW1"
    assert parsed["name"] == "Welcome"


def test_get_with_actions_fetches_subresource(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "data": {"id": "FLOW1", "type": "flow", "attributes": {"name": "Welcome"}}
        }
        client.paginate.return_value = iter(
            [
                {
                    "id": "ACT1",
                    "type": "flow-action",
                    "attributes": {"action_type": "SEND_EMAIL", "status": "live"},
                }
            ]
        )
        with patch.object(
            sys, "argv", ["get.py", "--id", "FLOW1", "--with-actions", "--output", "json"]
        ):
            assert getcmd.main() == 0
        _, kwargs = client.paginate.call_args
        assert client.paginate.call_args[0][0] == "flows/FLOW1/flow-actions"
        assert kwargs["limit"] == 50
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["flow"]["id"] == "FLOW1"
    assert parsed["actions"][0]["id"] == "ACT1"
    assert parsed["actions"][0]["action_type"] == "SEND_EMAIL"


def test_get_requires_id(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with patch.object(sys, "argv", ["get.py"]):
            try:
                getcmd.main()
            except SystemExit as exc:
                assert exc.code != 0
            else:
                raise AssertionError("expected SystemExit")
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_flows_get.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `klaviyo/scripts/flows/get.py`.** Complete code:

```python
"""Get a single Klaviyo flow by --id.

With --with-actions, also fetches the flow's flow-actions and returns a combined
``{flow, actions}`` object.
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


def _flatten_flow(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "name": attrs.get("name"),
        "status": attrs.get("status"),
        "archived": attrs.get("archived"),
        "trigger_type": attrs.get("trigger_type"),
        "created": attrs.get("created"),
        "updated": attrs.get("updated"),
    }


def _flatten_action(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "action_type": attrs.get("action_type"),
        "status": attrs.get("status"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get a Klaviyo flow by id.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Flow id")
    parser.add_argument(
        "--with-actions",
        dest="with_actions",
        action="store_true",
        help="Also fetch and include the flow's actions",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        body = client.get(f"flows/{args.id}")
        check_errors(body)
        flow = _flatten_flow(body.get("data") or {})
        if args.with_actions:
            actions = [
                _flatten_action(r)
                for r in client.paginate(
                    f"flows/{args.id}/flow-actions", limit=args.limit
                )
            ]
            print(format_output({"flow": flow, "actions": actions}, args.output))
            return 0

    print(format_output(flow, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_flows_get.py -v
uv run ruff check klaviyo/scripts/flows/get.py tests/klaviyo/scripts/test_flows_get.py
uv run ruff format klaviyo/scripts/flows/get.py tests/klaviyo/scripts/test_flows_get.py
git add klaviyo/scripts/flows/get.py tests/klaviyo/scripts/test_flows_get.py
git commit -m "feat(klaviyo): flows/get.py with --with-actions"
```

---

## Task 3: `flows/update_status.py` (reference gated mutation)

`PATCH /flows/{id}` to activate/deactivate a flow. High-stakes: `--yes`-gated (per spec §4). `--dry-run` works without `--yes` and prints the JSON:API body; live execution without `--yes` errors via `parser.error(...)` before any network call (mirrors `profiles/unsubscribe.py` and `lists/delete.py`).

**Files:**
- Create: `klaviyo/scripts/flows/update_status.py`
- Create: `tests/klaviyo/scripts/test_flows_update_status.py`

- [ ] **Step 1: Write failing test.** Write `tests/klaviyo/scripts/test_flows_update_status.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.flows import update_status as cmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.flows.update_status.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.flows.update_status.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_dry_run_builds_body_and_skips_patch_without_yes(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["update_status.py", "--id", "FLOW1", "--status", "live", "--dry-run", "--output", "json"],
        ):
            assert cmd.main() == 0
        assert client.patch.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "flow"
    assert parsed["data"]["id"] == "FLOW1"
    assert parsed["data"]["attributes"]["status"] == "live"


def test_without_yes_errors_in_live_mode(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["update_status.py", "--id", "FLOW1", "--status", "live"]
        ):
            try:
                cmd.main()
            except SystemExit as exc:
                assert exc.code != 0
            else:
                raise AssertionError("expected SystemExit")
        assert client.patch.call_count == 0


def test_with_yes_patches_flow(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.patch.return_value = {
            "data": {"id": "FLOW1", "type": "flow", "attributes": {"status": "live"}}
        }
        with patch.object(
            sys, "argv", ["update_status.py", "--id", "FLOW1", "--status", "live", "--yes"]
        ):
            assert cmd.main() == 0
        args, kwargs = client.patch.call_args
        assert args[0] == "flows/FLOW1"
        body = kwargs.get("json") or args[1]
        assert body["data"]["id"] == "FLOW1"
        assert body["data"]["attributes"]["status"] == "live"


def test_status_choices_enforced(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["update_status.py", "--id", "FLOW1", "--status", "bogus"]
        ):
            try:
                cmd.main()
            except SystemExit as exc:
                assert exc.code != 0
            else:
                raise AssertionError("expected SystemExit")
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_flows_update_status.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `klaviyo/scripts/flows/update_status.py`.** Complete code:

```python
"""Activate or deactivate a Klaviyo flow (status change).

High-stakes: --yes is required for live execution. --dry-run works without
--yes and prints the JSON:API PATCH body without calling the API.
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
    return {
        "data": {
            "type": "flow",
            "id": args.id,
            "attributes": {"status": args.status},
        }
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Activate or deactivate a Klaviyo flow."
    )
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Flow id")
    parser.add_argument(
        "--status",
        required=True,
        choices=("live", "manual", "draft"),
        help="Target flow status",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    if not args.yes:
        parser.error("--yes is required to confirm a flow status change; aborting")

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.patch(f"flows/{args.id}", json=body)

    check_errors(result)
    resource = result.get("data") or {}
    attrs = resource.get("attributes") or {}
    print(
        format_output(
            {"id": resource.get("id"), "status": attrs.get("status")}, args.output
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_flows_update_status.py -v
uv run ruff check klaviyo/scripts/flows/update_status.py tests/klaviyo/scripts/test_flows_update_status.py
uv run ruff format klaviyo/scripts/flows/update_status.py tests/klaviyo/scripts/test_flows_update_status.py
git add klaviyo/scripts/flows/update_status.py tests/klaviyo/scripts/test_flows_update_status.py
git commit -m "feat(klaviyo): flows/update_status.py gated on --yes"
```

---

## Task 4: `metrics/list.py` and `metrics/get.py`

Two straightforward reads. `GET /metrics` (paginated, flattened) and `GET /metrics/{id}` (single resource).

**Files:**
- Create: `klaviyo/scripts/metrics/__init__.py`
- Create: `klaviyo/scripts/metrics/list.py`
- Create: `klaviyo/scripts/metrics/get.py`
- Create: `tests/klaviyo/scripts/test_metrics_list.py`
- Create: `tests/klaviyo/scripts/test_metrics_get.py`

- [ ] **Step 1: Create the package marker.**

```bash
mkdir -p klaviyo/scripts/metrics
touch klaviyo/scripts/metrics/__init__.py
```

- [ ] **Step 2: Write failing tests.** Write `tests/klaviyo/scripts/test_metrics_list.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.metrics import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.metrics.list.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.metrics.list.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_metrics_list_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [
                {
                    "id": "MET1",
                    "type": "metric",
                    "attributes": {"name": "Placed Order", "integration": {"name": "Shopify"}},
                }
            ]
        )
        with patch.object(sys, "argv", ["list.py", "--output", "json"]):
            assert listcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "MET1"
    assert parsed[0]["name"] == "Placed Order"


def test_metrics_list_passes_limit(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py", "--limit", "7"]):
            assert listcmd.main() == 0
        _, kwargs = client.paginate.call_args
        assert kwargs["limit"] == 7
```

Write `tests/klaviyo/scripts/test_metrics_get.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.metrics import get as getcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.metrics.get.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.metrics.get.KlaviyoClient"))
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
            "data": {"id": "MET1", "type": "metric", "attributes": {"name": "Placed Order"}}
        }
        with patch.object(sys, "argv", ["get.py", "--id", "MET1", "--output", "json"]):
            assert getcmd.main() == 0
        client.get.assert_called_once_with("metrics/MET1")
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "MET1"
    assert parsed["name"] == "Placed Order"


def test_get_requires_id(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with patch.object(sys, "argv", ["get.py"]):
            try:
                getcmd.main()
            except SystemExit as exc:
                assert exc.code != 0
            else:
                raise AssertionError("expected SystemExit")
```

- [ ] **Step 3: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_metrics_list.py tests/klaviyo/scripts/test_metrics_get.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 4: Implement `klaviyo/scripts/metrics/list.py`.** Complete code:

```python
"""List Klaviyo metrics.

Flattens JSON:API metric resources (id, name, integration name) into flat rows.
Honors --limit via cursor pagination.
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
    integration = attrs.get("integration") or {}
    return {
        "id": resource.get("id"),
        "name": attrs.get("name"),
        "integration": integration.get("name"),
        "created": attrs.get("created"),
        "updated": attrs.get("updated"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Klaviyo metrics.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        rows = [_flatten(r) for r in client.paginate("metrics", limit=args.limit)]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Implement `klaviyo/scripts/metrics/get.py`.** Complete code:

```python
"""Get a single Klaviyo metric by --id."""

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
    parser = argparse.ArgumentParser(description="Get a Klaviyo metric by id.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Metric id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        body = client.get(f"metrics/{args.id}")

    check_errors(body)
    resource = body.get("data") or {}
    attrs = resource.get("attributes") or {}
    integration = attrs.get("integration") or {}
    print(
        format_output(
            {
                "id": resource.get("id"),
                "name": attrs.get("name"),
                "integration": integration.get("name"),
                "created": attrs.get("created"),
                "updated": attrs.get("updated"),
            },
            args.output,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_metrics_list.py tests/klaviyo/scripts/test_metrics_get.py -v
uv run ruff check klaviyo/scripts/metrics/list.py klaviyo/scripts/metrics/get.py tests/klaviyo/scripts/test_metrics_list.py tests/klaviyo/scripts/test_metrics_get.py
uv run ruff format klaviyo/scripts/metrics/list.py klaviyo/scripts/metrics/get.py tests/klaviyo/scripts/test_metrics_list.py tests/klaviyo/scripts/test_metrics_get.py
git add klaviyo/scripts/metrics/__init__.py klaviyo/scripts/metrics/list.py klaviyo/scripts/metrics/get.py tests/klaviyo/scripts/test_metrics_list.py tests/klaviyo/scripts/test_metrics_get.py
git commit -m "feat(klaviyo): metrics/list.py and metrics/get.py"
```

---

## Task 5: `metrics/aggregate.py` (reference POST-query script)

`POST /metric-aggregates`. A read-style query that uses POST with a JSON:API `metric-aggregate` body. The body shape is load-bearing: `measurements`, `interval`, `metric_id`, and time bounds live under `data.attributes`. `--dry-run` prints the body and returns 0.

**Files:**
- Create: `klaviyo/scripts/metrics/aggregate.py`
- Create: `tests/klaviyo/scripts/test_metrics_aggregate.py`

- [ ] **Step 1: Write failing test.** Write `tests/klaviyo/scripts/test_metrics_aggregate.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.metrics import aggregate as aggcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.metrics.aggregate.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.metrics.aggregate.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_aggregate_dry_run_builds_body_and_skips_post(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "aggregate.py",
                "--metric-id",
                "MET1",
                "--measurement",
                "count",
                "--interval",
                "day",
                "--start",
                "2026-01-01T00:00:00Z",
                "--end",
                "2026-01-31T00:00:00Z",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert aggcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "metric-aggregate"
    attrs = parsed["data"]["attributes"]
    assert attrs["metric_id"] == "MET1"
    assert attrs["measurements"] == ["count"]
    assert attrs["interval"] == "day"
    assert attrs["filter"] == [
        "greater-or-equal(datetime,2026-01-01T00:00:00Z)",
        "less-than(datetime,2026-01-31T00:00:00Z)",
    ]


def test_aggregate_posts_to_endpoint(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"data": {"type": "metric-aggregate", "attributes": {}}}
        with patch.object(
            sys,
            "argv",
            [
                "aggregate.py",
                "--metric-id",
                "MET1",
                "--measurement",
                "count",
                "--start",
                "2026-01-01T00:00:00Z",
                "--end",
                "2026-01-31T00:00:00Z",
            ],
        ):
            assert aggcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "metric-aggregates"
        body = kwargs.get("json") or args[1]
        assert body["data"]["attributes"]["metric_id"] == "MET1"
        assert body["data"]["attributes"]["measurements"] == ["count"]


def test_aggregate_multiple_measurements(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "aggregate.py",
                "--metric-id",
                "MET1",
                "--measurement",
                "count",
                "--measurement",
                "sum_value",
                "--start",
                "2026-01-01T00:00:00Z",
                "--end",
                "2026-01-31T00:00:00Z",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert aggcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["attributes"]["measurements"] == ["count", "sum_value"]
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_metrics_aggregate.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `klaviyo/scripts/metrics/aggregate.py`.** Complete code:

```python
"""Query a Klaviyo metric aggregate (POST /metric-aggregates).

A read-style query expressed as a JSON:API ``metric-aggregate`` body: the
metric id, one or more measurements, an interval, and a datetime window encoded
as JSON:API filter expressions. --dry-run prints the body and skips the POST.
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
    attributes: dict[str, object] = {
        "metric_id": args.metric_id,
        "measurements": list(args.measurement),
        "interval": args.interval,
        "filter": [
            f"greater-or-equal(datetime,{args.start})",
            f"less-than(datetime,{args.end})",
        ],
    }
    if args.timezone:
        attributes["timezone"] = args.timezone
    return {"data": {"type": "metric-aggregate", "attributes": attributes}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Query a Klaviyo metric aggregate."
    )
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--metric-id", dest="metric_id", required=True, help="Metric id")
    parser.add_argument(
        "--measurement",
        action="append",
        required=True,
        help="Measurement to aggregate (repeatable): count, sum_value, unique, ...",
    )
    parser.add_argument(
        "--interval",
        default="day",
        choices=("hour", "day", "week", "month"),
        help="Aggregation interval (default: day)",
    )
    parser.add_argument(
        "--start", required=True, help="ISO-8601 window start (inclusive), e.g. 2026-01-01T00:00:00Z"
    )
    parser.add_argument(
        "--end", required=True, help="ISO-8601 window end (exclusive), e.g. 2026-01-31T00:00:00Z"
    )
    parser.add_argument("--timezone", help="IANA timezone for bucketing, e.g. UTC")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("metric-aggregates", json=body)

    check_errors(result)
    print(format_output(result.get("data") or {}, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_metrics_aggregate.py -v
uv run ruff check klaviyo/scripts/metrics/aggregate.py tests/klaviyo/scripts/test_metrics_aggregate.py
uv run ruff format klaviyo/scripts/metrics/aggregate.py tests/klaviyo/scripts/test_metrics_aggregate.py
git add klaviyo/scripts/metrics/aggregate.py tests/klaviyo/scripts/test_metrics_aggregate.py
git commit -m "feat(klaviyo): metrics/aggregate.py POST query with --dry-run"
```

---

## Task 6: `events/list.py` and `events/create.py`

`GET /events` (filters by metric/profile/time, paginated) and `POST /events` (track an event; low-risk, `--dry-run` only, not `--yes`-gated).

**Files:**
- Create: `klaviyo/scripts/events/__init__.py`
- Create: `klaviyo/scripts/events/list.py`
- Create: `klaviyo/scripts/events/create.py`
- Create: `tests/klaviyo/scripts/test_events_list.py`
- Create: `tests/klaviyo/scripts/test_events_create.py`

- [ ] **Step 1: Create the package marker.**

```bash
mkdir -p klaviyo/scripts/events
touch klaviyo/scripts/events/__init__.py
```

- [ ] **Step 2: Write failing tests.** Write `tests/klaviyo/scripts/test_events_list.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.events import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.events.list.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.events.list.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_events_list_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [
                {
                    "id": "EVT1",
                    "type": "event",
                    "attributes": {"datetime": "2026-01-02T03:04:05Z", "event_properties": {"x": 1}},
                }
            ]
        )
        with patch.object(sys, "argv", ["list.py", "--output", "json"]):
            assert listcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "EVT1"
    assert parsed[0]["datetime"] == "2026-01-02T03:04:05Z"


def test_events_list_metric_filter_builds_param(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py", "--metric-id", "MET1"]):
            assert listcmd.main() == 0
        _, kwargs = client.paginate.call_args
        assert kwargs["params"]["filter"] == 'equals(metric_id,"MET1")'


def test_events_list_combines_filters(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(
            sys, "argv", ["list.py", "--profile-id", "P1", "--since", "2026-01-01T00:00:00Z"]
        ):
            assert listcmd.main() == 0
        _, kwargs = client.paginate.call_args
        assert kwargs["params"]["filter"] == (
            'and(equals(profile_id,"P1"),greater-or-equal(datetime,2026-01-01T00:00:00Z))'
        )
```

Write `tests/klaviyo/scripts/test_events_create.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from klaviyo.scripts.events import create as createcmd
from klaviyo.utils.client import KlaviyoAPIError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.events.create.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.events.create.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_create_dry_run_builds_body_and_skips_post(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "create.py",
                "--metric-name",
                "Viewed Demo",
                "--email",
                "a@b.com",
                "--properties",
                '{"plan": "pro"}',
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "event"
    attrs = parsed["data"]["attributes"]
    assert attrs["metric"]["data"]["attributes"]["name"] == "Viewed Demo"
    assert attrs["profile"]["data"]["attributes"]["email"] == "a@b.com"
    assert attrs["properties"] == {"plan": "pro"}


def test_create_posts_to_events_endpoint(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {}
        with patch.object(
            sys, "argv", ["create.py", "--metric-name", "Viewed Demo", "--email", "a@b.com"]
        ):
            assert createcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "events"
        body = kwargs.get("json") or args[1]
        assert body["data"]["attributes"]["metric"]["data"]["attributes"]["name"] == "Viewed Demo"


def test_create_invalid_properties_json_errors(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["create.py", "--metric-name", "X", "--email", "a@b.com", "--properties", "not-json"],
        ):
            try:
                createcmd.main()
            except SystemExit as exc:
                assert exc.code != 0
            else:
                raise AssertionError("expected SystemExit")


def test_create_surfaces_api_error(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"errors": [{"detail": "bad metric"}]}
        with (
            patch.object(sys, "argv", ["create.py", "--metric-name", "X", "--email", "a@b.com"]),
            pytest.raises(KlaviyoAPIError),
        ):
            createcmd.main()
```

- [ ] **Step 3: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_events_list.py tests/klaviyo/scripts/test_events_create.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 4: Implement `klaviyo/scripts/events/list.py`.** Complete code:

```python
"""List Klaviyo events with optional filters.

Filters: --metric-id, --profile-id, --since (ISO-8601 lower bound). When more
than one is given they are combined with a JSON:API ``and(...)`` expression.
Flattens event resources into flat rows; honors --limit via pagination.
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
        "datetime": attrs.get("datetime"),
        "timestamp": attrs.get("timestamp"),
        "uuid": attrs.get("uuid"),
    }


def _build_filter(args: argparse.Namespace) -> str | None:
    clauses: list[str] = []
    if args.metric_id:
        clauses.append(f'equals(metric_id,"{args.metric_id}")')
    if args.profile_id:
        clauses.append(f'equals(profile_id,"{args.profile_id}")')
    if args.since:
        clauses.append(f"greater-or-equal(datetime,{args.since})")
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return f"and({','.join(clauses)})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Klaviyo events.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--metric-id", dest="metric_id", help="Filter by metric id")
    parser.add_argument("--profile-id", dest="profile_id", help="Filter by profile id")
    parser.add_argument(
        "--since", help="Lower bound on event datetime (ISO-8601), e.g. 2026-01-01T00:00:00Z"
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    params: dict[str, object] = {}
    flt = _build_filter(args)
    if flt:
        params["filter"] = flt

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        rows = [_flatten(r) for r in client.paginate("events", params=params, limit=args.limit)]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Implement `klaviyo/scripts/events/create.py`.** Complete code:

```python
"""Track a Klaviyo event (POST /events).

Builds a JSON:API ``event`` body referencing a metric (by name) and a profile
(by email). Optional --properties is a JSON object of event properties.
Low-risk; --dry-run prints the body and skips the POST (no --yes gate).
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
from klaviyo.utils.cli import (
    add_common_flags,
    add_klaviyo_flags,
    configure_logging_from_args,
    format_output,
)
from klaviyo.utils.client import KlaviyoClient, check_errors


def _build_body(args: argparse.Namespace, properties: dict) -> dict:
    profile_attrs: dict[str, object] = {}
    if args.email:
        profile_attrs["email"] = args.email
    if args.phone_number:
        profile_attrs["phone_number"] = args.phone_number
    attributes: dict[str, object] = {
        "metric": {"data": {"type": "metric", "attributes": {"name": args.metric_name}}},
        "profile": {"data": {"type": "profile", "attributes": profile_attrs}},
        "properties": properties,
    }
    if args.value is not None:
        attributes["value"] = args.value
    if args.time:
        attributes["time"] = args.time
    return {"data": {"type": "event", "attributes": attributes}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Track a Klaviyo event.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument(
        "--metric-name", dest="metric_name", required=True, help="Metric name to record"
    )
    parser.add_argument("--email", help="Profile email")
    parser.add_argument("--phone-number", dest="phone_number", help="E.164 phone number")
    parser.add_argument(
        "--properties", help="Event properties as a JSON object string", default="{}"
    )
    parser.add_argument("--value", type=float, help="Numeric event value (e.g. order total)")
    parser.add_argument("--time", help="Event time (ISO-8601); defaults to now server-side")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if not args.email and not args.phone_number:
        parser.error("at least one of --email or --phone-number is required")

    try:
        properties = json.loads(args.properties)
    except json.JSONDecodeError as exc:
        parser.error(f"--properties is not valid JSON: {exc}")

    body = _build_body(args, properties)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("events", json=body)

    check_errors(result)
    print(f"Tracked event {args.metric_name!r} (accepted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_events_list.py tests/klaviyo/scripts/test_events_create.py -v
uv run ruff check klaviyo/scripts/events/list.py klaviyo/scripts/events/create.py tests/klaviyo/scripts/test_events_list.py tests/klaviyo/scripts/test_events_create.py
uv run ruff format klaviyo/scripts/events/list.py klaviyo/scripts/events/create.py tests/klaviyo/scripts/test_events_list.py tests/klaviyo/scripts/test_events_create.py
git add klaviyo/scripts/events/__init__.py klaviyo/scripts/events/list.py klaviyo/scripts/events/create.py tests/klaviyo/scripts/test_events_list.py tests/klaviyo/scripts/test_events_create.py
git commit -m "feat(klaviyo): events/list.py and events/create.py"
```

---

## Task 7: `reports/campaign.py` and `reports/flow.py` (POST reporting queries)

`POST /campaign-values-reports` and `POST /flow-values-reports`. Both are read-style POST queries with a JSON:API `*-values-report` body whose shape is the load-bearing test surface: `statistics`, `timeframe`, optional `conversion_metric_id`, and a `filter`. For flow reports the interval (`daily`/`weekly`/`monthly`) is part of `attributes`. `--dry-run` prints the body and returns 0.

**Files:**
- Create: `klaviyo/scripts/reports/__init__.py`
- Create: `klaviyo/scripts/reports/campaign.py`
- Create: `klaviyo/scripts/reports/flow.py`
- Create: `tests/klaviyo/scripts/test_reports_campaign.py`
- Create: `tests/klaviyo/scripts/test_reports_flow.py`

- [ ] **Step 1: Create the package marker.**

```bash
mkdir -p klaviyo/scripts/reports
touch klaviyo/scripts/reports/__init__.py
```

- [ ] **Step 2: Write failing tests.** Write `tests/klaviyo/scripts/test_reports_campaign.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.reports import campaign as cmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.reports.campaign.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.reports.campaign.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_campaign_report_dry_run_builds_body_and_skips_post(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "campaign.py",
                "--statistic",
                "opens",
                "--statistic",
                "clicks",
                "--timeframe",
                "last_30_days",
                "--conversion-metric-id",
                "MET1",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert cmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "campaign-values-report"
    attrs = parsed["data"]["attributes"]
    assert attrs["statistics"] == ["opens", "clicks"]
    assert attrs["timeframe"] == {"key": "last_30_days"}
    assert attrs["conversion_metric_id"] == "MET1"


def test_campaign_report_posts_to_endpoint(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"data": {"type": "campaign-values-report", "attributes": {}}}
        with patch.object(
            sys,
            "argv",
            [
                "campaign.py",
                "--statistic",
                "opens",
                "--timeframe",
                "last_30_days",
                "--conversion-metric-id",
                "MET1",
            ],
        ):
            assert cmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "campaign-values-reports"
        body = kwargs.get("json") or args[1]
        assert body["data"]["attributes"]["statistics"] == ["opens"]
```

Write `tests/klaviyo/scripts/test_reports_flow.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.reports import flow as cmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.reports.flow.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.reports.flow.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_flow_report_dry_run_builds_body_with_interval(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "flow.py",
                "--statistic",
                "opens",
                "--timeframe",
                "last_30_days",
                "--conversion-metric-id",
                "MET1",
                "--interval",
                "weekly",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert cmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "flow-values-report"
    attrs = parsed["data"]["attributes"]
    assert attrs["statistics"] == ["opens"]
    assert attrs["timeframe"] == {"key": "last_30_days"}
    assert attrs["interval"] == "weekly"
    assert attrs["conversion_metric_id"] == "MET1"


def test_flow_report_posts_to_endpoint(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"data": {"type": "flow-values-report", "attributes": {}}}
        with patch.object(
            sys,
            "argv",
            [
                "flow.py",
                "--statistic",
                "opens",
                "--timeframe",
                "last_30_days",
                "--conversion-metric-id",
                "MET1",
            ],
        ):
            assert cmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "flow-values-reports"
        body = kwargs.get("json") or args[1]
        assert body["data"]["attributes"]["interval"] == "daily"
```

- [ ] **Step 3: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_reports_campaign.py tests/klaviyo/scripts/test_reports_flow.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 4: Implement `klaviyo/scripts/reports/campaign.py`.** Complete code:

```python
"""Query a Klaviyo campaign performance report (POST /campaign-values-reports).

A read-style POST query: a JSON:API ``campaign-values-report`` body carrying the
requested statistics, a timeframe (a preset key), the conversion metric id, and
an optional filter. --dry-run prints the body and skips the POST.
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
    attributes: dict[str, object] = {
        "statistics": list(args.statistic),
        "timeframe": {"key": args.timeframe},
        "conversion_metric_id": args.conversion_metric_id,
    }
    if args.filter:
        attributes["filter"] = args.filter
    return {"data": {"type": "campaign-values-report", "attributes": attributes}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Query a Klaviyo campaign performance report."
    )
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument(
        "--statistic",
        action="append",
        required=True,
        help="Statistic to include (repeatable): opens, clicks, revenue, ...",
    )
    parser.add_argument(
        "--timeframe",
        default="last_30_days",
        help="Preset timeframe key (e.g. last_30_days, last_12_months)",
    )
    parser.add_argument(
        "--conversion-metric-id",
        dest="conversion_metric_id",
        required=True,
        help="Conversion metric id (e.g. Placed Order metric)",
    )
    parser.add_argument(
        "--filter", help="Optional JSON:API filter expression to scope the report"
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("campaign-values-reports", json=body)

    check_errors(result)
    print(format_output(result.get("data") or {}, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Implement `klaviyo/scripts/reports/flow.py`.** Complete code:

```python
"""Query a Klaviyo flow performance report (POST /flow-values-reports).

Like the campaign report, but the JSON:API ``flow-values-report`` body also
carries an ``interval`` (daily/weekly/monthly). --dry-run prints the body and
skips the POST.
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
    attributes: dict[str, object] = {
        "statistics": list(args.statistic),
        "timeframe": {"key": args.timeframe},
        "conversion_metric_id": args.conversion_metric_id,
        "interval": args.interval,
    }
    if args.filter:
        attributes["filter"] = args.filter
    return {"data": {"type": "flow-values-report", "attributes": attributes}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Query a Klaviyo flow performance report."
    )
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument(
        "--statistic",
        action="append",
        required=True,
        help="Statistic to include (repeatable): opens, clicks, revenue, ...",
    )
    parser.add_argument(
        "--timeframe",
        default="last_30_days",
        help="Preset timeframe key (e.g. last_30_days, last_12_months)",
    )
    parser.add_argument(
        "--conversion-metric-id",
        dest="conversion_metric_id",
        required=True,
        help="Conversion metric id (e.g. Placed Order metric)",
    )
    parser.add_argument(
        "--interval",
        default="daily",
        choices=("daily", "weekly", "monthly"),
        help="Reporting interval (default: daily)",
    )
    parser.add_argument(
        "--filter", help="Optional JSON:API filter expression to scope the report"
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("flow-values-reports", json=body)

    check_errors(result)
    print(format_output(result.get("data") or {}, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_reports_campaign.py tests/klaviyo/scripts/test_reports_flow.py -v
uv run ruff check klaviyo/scripts/reports/campaign.py klaviyo/scripts/reports/flow.py tests/klaviyo/scripts/test_reports_campaign.py tests/klaviyo/scripts/test_reports_flow.py
uv run ruff format klaviyo/scripts/reports/campaign.py klaviyo/scripts/reports/flow.py tests/klaviyo/scripts/test_reports_campaign.py tests/klaviyo/scripts/test_reports_flow.py
git add klaviyo/scripts/reports/__init__.py klaviyo/scripts/reports/campaign.py klaviyo/scripts/reports/flow.py tests/klaviyo/scripts/test_reports_campaign.py tests/klaviyo/scripts/test_reports_flow.py
git commit -m "feat(klaviyo): reports/campaign.py and reports/flow.py POST queries"
```

---

## Task 8: Skills — `klaviyo-flows` and `klaviyo-metrics`

Mirror the `skills/shopify-webhooks/SKILL.md` and `skills/klaviyo-*/SKILL.md` front-matter shape: a `name:` line and a single-paragraph `description:` packed with trigger phrases and the per-script flag posture (which scripts honor `--dry-run`, which require `--yes`), then a body covering when to use, each script, and a "defer to direct API use" note for unsupported operations.

**Files:**
- Create: `skills/klaviyo-flows/SKILL.md`
- Create: `skills/klaviyo-metrics/SKILL.md`

- [ ] **Step 1: Write `skills/klaviyo-flows/SKILL.md`.** Covers `flows/{list,get,update_status}` and `events/{list,create}` (events folded in here as flow-adjacent activity). Front-matter `description` must name triggers: "list Klaviyo flows", "show flow details", "show flow actions", "activate a flow", "deactivate a flow", "turn a flow live", "list events", "track an event". Note `--dry-run` on `update_status`/`events/create` and that `flows/update_status` requires `--yes` for live execution. Note that flow definition/authoring (adding actions, editing branches) is deferred to direct API/UI use.

- [ ] **Step 2: Write `skills/klaviyo-metrics/SKILL.md`.** Covers `metrics/{list,get,aggregate}` and `reports/{campaign,flow}`. Triggers: "list metrics", "show a metric", "metric aggregate", "how many placed orders", "campaign performance report", "flow performance report", "open rate", "click rate", "revenue report". Note that `aggregate`/`reports` are POST queries (no mutation) but still honor `--dry-run` to preview the JSON:API request body; none are `--yes`-gated. Document the `--conversion-metric-id` requirement for reports.

- [ ] **Step 3: Commit.**

```bash
git add skills/klaviyo-flows/SKILL.md skills/klaviyo-metrics/SKILL.md
git commit -m "docs(klaviyo): klaviyo-flows and klaviyo-metrics skills"
```

---

## Task 9: Full sweep, CHANGELOG, domain tag

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Run the whole suite.**

```bash
uv run pytest tests/klaviyo/ -v
```
Expected: every K1 + K3 test passes (K2 too if present). No live calls.

- [ ] **Step 2: Ruff-clean the whole domain.**

```bash
uv run ruff check klaviyo/ tests/klaviyo/
uv run ruff format --check klaviyo/ tests/klaviyo/
```
Expected: no findings.

- [ ] **Step 3: Smoke each new script's `--help` and a representative `--dry-run` (no API key, no `--yes`).**

```bash
uv run klaviyo/scripts/flows/update_status.py --id FLOW1 --status live --dry-run --output json
uv run klaviyo/scripts/metrics/aggregate.py --metric-id MET1 --measurement count --start 2026-01-01T00:00:00Z --end 2026-01-31T00:00:00Z --dry-run --output json
uv run klaviyo/scripts/reports/campaign.py --statistic opens --conversion-metric-id MET1 --dry-run --output json
uv run klaviyo/scripts/reports/flow.py --statistic opens --conversion-metric-id MET1 --interval weekly --dry-run --output json
uv run klaviyo/scripts/events/create.py --metric-name "Viewed Demo" --email a@b.com --dry-run --output json
```
Expected: each prints the JSON:API body it would send and exits 0 without needing a real API key or `--yes`.

- [ ] **Step 4: Update `CHANGELOG.md`.** Add an entry under a new version heading (bump the patch/minor line per the prior K1/K2 entries; e.g. `## [0.7.0] — 2026-05-29`) noting: Klaviyo reporting cluster (flows list/get/update_status with `--yes` on the status change; metrics list/get/aggregate; events list/create; campaign + flow performance reports) and that the Klaviyo domain is now complete across audience/sending/reporting.

- [ ] **Step 5: Commit the CHANGELOG.**

```bash
git add CHANGELOG.md
git commit -m "docs(klaviyo): CHANGELOG for Klaviyo reporting (K3) + domain complete"
```

- [ ] **Step 6: Tag the completed Klaviyo domain.** Per spec §12, the domain is tagged when K3 lands.

```bash
git tag -a v0.7.0 -m "Klaviyo domain complete (audience + sending + reporting)"
```
(Use the version chosen in Step 4; do not push the tag unless the user asks.)

---

## Definition of Done

Scoped to K3 (the reporting cluster) and the domain-level finish (spec §12):

- [ ] `flows/{list,get,update_status}` implemented and unit-tested; `update_status` is `--yes`-gated (live execution without `--yes` errors before any network call) and prints its JSON:API body under `--dry-run`.
- [ ] `metrics/{list,get,aggregate}` implemented and unit-tested; `aggregate` is a POST query whose `metric-aggregate` body shape (measurements, interval, datetime filter) is asserted in tests.
- [ ] `events/{list,create}` implemented and unit-tested; `create` honors `--dry-run`, validates `--properties` JSON, and is not `--yes`-gated.
- [ ] `reports/{campaign,flow}` implemented and unit-tested; both are POST queries whose `*-values-report` body shape (statistics, timeframe, conversion_metric_id, and flow `interval`) is asserted in tests; both honor `--dry-run`.
- [ ] Every new script follows repo conventions: `sys.path` bootstrap, `main(argv=None) -> int`, `if __name__ == "__main__": sys.exit(main())`, common + klaviyo CLI flags, `KlaviyoClient` as context manager, `check_errors` on responses.
- [ ] All tests mock `KlaviyoClient`; no live calls; `uv run pytest tests/klaviyo/` green.
- [ ] `klaviyo-flows` and `klaviyo-metrics` skills written, covering each script's `--dry-run`/`--yes` posture and deferring flow authoring to direct API use.
- [ ] Whole Klaviyo domain is ruff-clean (`ruff check` + `ruff format --check`).
- [ ] `CHANGELOG.md` bumped with the K3 / domain-complete entry.
- [ ] The full Klaviyo domain is tagged (audience + sending + reporting), per spec §12.
