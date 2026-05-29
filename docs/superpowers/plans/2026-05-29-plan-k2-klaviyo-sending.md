# Plan K2: Klaviyo Campaigns + Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the Klaviyo sending cluster — full lifecycle management of campaigns (`list/get/create/schedule/cancel/delete`) and email templates (`list/get/create/update/delete/render/clone/assign`) — as `uv run klaviyo/scripts/<cluster>/<op>.py` scripts on the K1 foundation, with `--dry-run` on every mutation and `--yes` gating the high-stakes set.

**Architecture:** Each script is one operation built on the K1 `KlaviyoClient` (JSON:API over `core.http.HttpClient`; `Klaviyo-API-Key` auth; dated `revision` header from `domains.klaviyo.api_version`; `check_errors` raising `KlaviyoAPIError`). Reads flatten JSON:API resources into flat rows; mutations build a JSON:API body, print it under `--dry-run` and return 0 without calling the API, else POST/PATCH/DELETE then `check_errors`. The send/cancel path is the only place where the exact endpoint shape is revision-dependent, so Task 4 forces a documentation check before any code is written.

**Tech Stack:** `httpx>=0.27`, `pyyaml>=6`, `pydantic>=2.7` (the `klaviyo` extra populated in K1). Tests use `pytest` with `monkeypatch`/`unittest.mock.patch`. No vendor SDK, no MCP.

**Spec reference:** `docs/superpowers/specs/2026-05-29-klaviyo-domain-design.md` §4 (conventions — `--dry-run`/`--yes`, flattening), §5 K2 (sending script inventory — note the schedule/cancel endpoint caveat in the table), §7 (error handling), §8 (testing), §10 (skills), §11 (implementation split — Plan K2), §12 (definition of done, scoped here to K2).

**Depends on:** Plan K1 — `klaviyo/utils/client.py` (`KlaviyoClient`, `KlaviyoAPIError`, `ResourceNotFoundError`, `check_errors`, `_DEFAULT_REVISION`), `klaviyo/utils/cli.py` (`add_common_flags`, `add_klaviyo_flags`, `configure_logging_from_args`, `format_output`), the populated `klaviyo` extra, `domains.klaviyo` config, and CI `--extra klaviyo`. No `core/` changes. The Shopify domain (`shopify/scripts/webhooks/*`) remains the reference for script/test shape.

---

## File Structure

| Path | Responsibility |
|---|---|
| `klaviyo/scripts/campaigns/__init__.py` | empty package marker |
| `klaviyo/scripts/campaigns/list.py` | `GET /campaigns` — mandatory `messages.channel` filter (default `email`), pagination |
| `klaviyo/scripts/campaigns/get.py` | `GET /campaigns/{id}` |
| `klaviyo/scripts/campaigns/create.py` | `POST /campaigns` (`--dry-run`) |
| `klaviyo/scripts/campaigns/schedule.py` | Schedule a campaign send (`--dry-run`, `--yes`) — endpoint confirmed in Task 4 |
| `klaviyo/scripts/campaigns/cancel.py` | Cancel/revert a scheduled send (`--dry-run`, `--yes`) — endpoint confirmed in Task 4 |
| `klaviyo/scripts/campaigns/delete.py` | `DELETE /campaigns/{id}` (`--dry-run`, `--yes`) |
| `klaviyo/scripts/templates/__init__.py` | empty package marker |
| `klaviyo/scripts/templates/list.py` | `GET /templates` |
| `klaviyo/scripts/templates/get.py` | `GET /templates/{id}` |
| `klaviyo/scripts/templates/create.py` | `POST /templates` (`--dry-run`) |
| `klaviyo/scripts/templates/update.py` | `PATCH /templates/{id}` (`--dry-run`) |
| `klaviyo/scripts/templates/delete.py` | `DELETE /templates/{id}` (`--dry-run`, `--yes`) |
| `klaviyo/scripts/templates/render.py` | `POST /template-render` (`--dry-run`) |
| `klaviyo/scripts/templates/clone.py` | `POST /template-clone` (`--dry-run`) |
| `klaviyo/scripts/templates/assign.py` | `POST /campaign-message-assign-template` (`--dry-run`) |
| `tests/klaviyo/scripts/test_campaigns_*.py` | campaigns script tests |
| `tests/klaviyo/scripts/test_templates_*.py` | templates script tests |
| `docs/superpowers/notes/klaviyo-send-endpoint.md` | Recorded finding from Task 4's endpoint verification |
| `skills/klaviyo-campaigns/SKILL.md` | campaigns cluster skill |
| `skills/klaviyo-templates/SKILL.md` | templates cluster skill |
| `CHANGELOG.md` | bump for K2 (modify) |

---

## Task 1: `campaigns/list.py` (reference read script)

`GET /campaigns`. Klaviyo **mandates** a `filter` on `messages.channel`; this script defaults it to `email` and exposes `--channel`. Flatten JSON:API campaign resources into flat rows; honor `--limit` via `paginate`.

**Files:**
- Create: `klaviyo/scripts/campaigns/__init__.py`
- Create: `klaviyo/scripts/campaigns/list.py`
- Create: `tests/klaviyo/scripts/test_campaigns_list.py`

- [ ] **Step 1: Create the campaigns package marker.**

```bash
mkdir -p klaviyo/scripts/campaigns tests/klaviyo/scripts
touch klaviyo/scripts/campaigns/__init__.py
```

- [ ] **Step 2: Write failing test.** Write `tests/klaviyo/scripts/test_campaigns_list.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.campaigns import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.campaigns.list.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.campaigns.list.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_campaigns_list_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [
                {
                    "id": "CMP1",
                    "type": "campaign",
                    "attributes": {"name": "Spring Sale", "status": "Draft"},
                }
            ]
        )
        with patch.object(sys, "argv", ["list.py", "--output", "json"]):
            assert listcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "CMP1"
    assert parsed[0]["name"] == "Spring Sale"
    assert parsed[0]["status"] == "Draft"


def test_campaigns_list_default_channel_filter(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py"]):
            assert listcmd.main() == 0
        _, kwargs = client.paginate.call_args
        assert kwargs["params"]["filter"] == 'equals(messages.channel,"email")'


def test_campaigns_list_channel_override(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py", "--channel", "sms"]):
            assert listcmd.main() == 0
        _, kwargs = client.paginate.call_args
        assert kwargs["params"]["filter"] == 'equals(messages.channel,"sms")'
        assert kwargs["limit"] == 50
```

- [ ] **Step 3: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_campaigns_list.py -v
```
Expected: `ModuleNotFoundError: No module named 'klaviyo.scripts.campaigns.list'`.

- [ ] **Step 4: Implement `klaviyo/scripts/campaigns/list.py`.** Complete code:

```python
"""List Klaviyo campaigns.

Klaviyo's /campaigns endpoint requires a filter on messages.channel; this
script defaults it to "email" and exposes --channel. Flattens JSON:API campaign
resources into flat rows and honors --limit via cursor pagination.
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
        "created_at": attrs.get("created_at"),
        "scheduled_at": attrs.get("scheduled_at"),
        "send_time": attrs.get("send_time"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Klaviyo campaigns.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument(
        "--channel",
        default="email",
        help="Message channel to filter by (Klaviyo requires this; default email)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    params = {"filter": f'equals(messages.channel,"{args.channel}")'}

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        rows = [
            _flatten(r) for r in client.paginate("campaigns", params=params, limit=args.limit)
        ]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run, confirm pass.**

```bash
uv run pytest tests/klaviyo/scripts/test_campaigns_list.py -v
```
Expected: all tests pass.

- [ ] **Step 6: Ruff + commit.**

```bash
uv run ruff check klaviyo/scripts/campaigns/list.py tests/klaviyo/scripts/test_campaigns_list.py
uv run ruff format klaviyo/scripts/campaigns/list.py tests/klaviyo/scripts/test_campaigns_list.py
git add klaviyo/scripts/campaigns/__init__.py klaviyo/scripts/campaigns/list.py tests/klaviyo/scripts/test_campaigns_list.py
git commit -m "feat(klaviyo): campaigns/list.py with mandatory channel filter"
```

---

## Task 2: `campaigns/get.py`

`GET /campaigns/{id}`. Single-resource read; flatten the resource.

**Files:**
- Create: `klaviyo/scripts/campaigns/get.py`
- Create: `tests/klaviyo/scripts/test_campaigns_get.py`

- [ ] **Step 1: Write failing test.** Write `tests/klaviyo/scripts/test_campaigns_get.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.campaigns import get as getcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.campaigns.get.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.campaigns.get.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_get_campaign_by_id(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "data": {
                "id": "CMP1",
                "type": "campaign",
                "attributes": {"name": "Spring Sale", "status": "Draft"},
            }
        }
        with patch.object(sys, "argv", ["get.py", "--id", "CMP1", "--output", "json"]):
            assert getcmd.main() == 0
        client.get.assert_called_once_with("campaigns/CMP1")
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "CMP1"
    assert parsed["name"] == "Spring Sale"
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_campaigns_get.py -v
```

- [ ] **Step 3: Implement `klaviyo/scripts/campaigns/get.py`.** Complete code:

```python
"""Get a single Klaviyo campaign by id."""

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


def _flatten(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "name": attrs.get("name"),
        "status": attrs.get("status"),
        "created_at": attrs.get("created_at"),
        "scheduled_at": attrs.get("scheduled_at"),
        "send_time": attrs.get("send_time"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get a Klaviyo campaign by id.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Campaign id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        body = client.get(f"campaigns/{args.id}")
        check_errors(body)
        resource = body.get("data") or {}

    print(format_output(_flatten(resource), args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_campaigns_get.py -v
uv run ruff check klaviyo/scripts/campaigns/get.py tests/klaviyo/scripts/test_campaigns_get.py
uv run ruff format klaviyo/scripts/campaigns/get.py tests/klaviyo/scripts/test_campaigns_get.py
git add klaviyo/scripts/campaigns/get.py tests/klaviyo/scripts/test_campaigns_get.py
git commit -m "feat(klaviyo): campaigns/get.py"
```

---

## Task 3: `campaigns/create.py` (reference mutation script)

`POST /campaigns`. Builds a JSON:API `campaign` resource: a name plus a `campaign-messages` relationship carrying one message with its channel and audience (list/segment ids). `--dry-run` prints the body and skips the POST.

> Note: Klaviyo's campaign create body nests messages and audiences. This task models the common single-message email campaign (name, channel, subject, from, one list/segment audience). Richer multi-message campaigns are deferred to direct API use; the skill (Task 9) documents that.

**Files:**
- Create: `klaviyo/scripts/campaigns/create.py`
- Create: `tests/klaviyo/scripts/test_campaigns_create.py`

- [ ] **Step 1: Write failing test.** Write `tests/klaviyo/scripts/test_campaigns_create.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from klaviyo.scripts.campaigns import create as createcmd
from klaviyo.utils.client import KlaviyoAPIError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.campaigns.create.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.campaigns.create.KlaviyoClient")
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
                "--name",
                "Spring Sale",
                "--list-id",
                "LST1",
                "--subject",
                "20% off",
                "--from-email",
                "hi@shop.com",
                "--from-label",
                "Shop",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "campaign"
    assert parsed["data"]["attributes"]["name"] == "Spring Sale"
    msg = parsed["data"]["attributes"]["campaign-messages"]["data"][0]
    assert msg["attributes"]["definition"]["channel"] == "email"
    assert msg["attributes"]["definition"]["content"]["subject"] == "20% off"
    audiences = parsed["data"]["attributes"]["audiences"]
    assert audiences["included"] == ["LST1"]


def test_create_posts_jsonapi_body(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {
            "data": {"id": "CMP9", "type": "campaign", "attributes": {"name": "Spring Sale"}}
        }
        with patch.object(
            sys,
            "argv",
            [
                "create.py",
                "--name",
                "Spring Sale",
                "--list-id",
                "LST1",
                "--subject",
                "20% off",
                "--from-email",
                "hi@shop.com",
                "--from-label",
                "Shop",
            ],
        ):
            assert createcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "campaigns"
        body = kwargs.get("json") or args[1]
        assert body["data"]["attributes"]["name"] == "Spring Sale"


def test_create_surfaces_api_error(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {
            "errors": [{"detail": "invalid audience", "source": {"pointer": "/data"}}]
        }
        with (
            patch.object(
                sys,
                "argv",
                [
                    "create.py",
                    "--name",
                    "Spring Sale",
                    "--list-id",
                    "LST1",
                    "--subject",
                    "x",
                    "--from-email",
                    "hi@shop.com",
                    "--from-label",
                    "Shop",
                ],
            ),
            pytest.raises(KlaviyoAPIError),
        ):
            createcmd.main()
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_campaigns_create.py -v
```

- [ ] **Step 3: Implement `klaviyo/scripts/campaigns/create.py`.** Complete code:

```python
"""Create a Klaviyo email campaign (single-message).

Builds a JSON:API ``campaign`` resource with one email message and one
list/segment audience. --dry-run prints the request body and skips the POST.
Richer multi-message campaigns are deferred to direct API use.
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
    content: dict[str, object] = {
        "subject": args.subject,
        "from_email": args.from_email,
        "from_label": args.from_label,
    }
    if args.preview_text:
        content["preview_text"] = args.preview_text
    message = {
        "type": "campaign-message",
        "attributes": {
            "definition": {
                "channel": args.channel,
                "label": args.name,
                "content": content,
            }
        },
    }
    audiences: dict[str, list[str]] = {"included": [], "excluded": []}
    if args.list_id:
        audiences["included"].append(args.list_id)
    if args.segment_id:
        audiences["included"].append(args.segment_id)
    if args.exclude_id:
        audiences["excluded"].append(args.exclude_id)
    return {
        "data": {
            "type": "campaign",
            "attributes": {
                "name": args.name,
                "audiences": audiences,
                "campaign-messages": {"data": [message]},
            },
        }
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a Klaviyo email campaign.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--name", required=True, help="Campaign name")
    parser.add_argument("--subject", required=True, help="Email subject line")
    parser.add_argument("--from-email", dest="from_email", required=True, help="Sender email")
    parser.add_argument("--from-label", dest="from_label", required=True, help="Sender label")
    parser.add_argument("--preview-text", dest="preview_text", help="Email preview text")
    parser.add_argument("--channel", default="email", help="Message channel (default email)")
    parser.add_argument("--list-id", dest="list_id", help="Included list id")
    parser.add_argument("--segment-id", dest="segment_id", help="Included segment id")
    parser.add_argument("--exclude-id", dest="exclude_id", help="Excluded list/segment id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if not args.list_id and not args.segment_id:
        parser.error("at least one of --list-id or --segment-id is required")

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("campaigns", json=body)

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

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_campaigns_create.py -v
uv run ruff check klaviyo/scripts/campaigns/create.py tests/klaviyo/scripts/test_campaigns_create.py
uv run ruff format klaviyo/scripts/campaigns/create.py tests/klaviyo/scripts/test_campaigns_create.py
git add klaviyo/scripts/campaigns/create.py tests/klaviyo/scripts/test_campaigns_create.py
git commit -m "feat(klaviyo): campaigns/create.py with --dry-run"
```

---

## Task 4: VERIFY the send/cancel endpoint for the configured revision (BLOCKING — do before Tasks 5 & 6)

**Do not hard-assume the schedule/cancel endpoint shape.** Klaviyo has, across revisions, moved between a `campaign-send-jobs` resource and a campaign `send_strategy`/`scheduled_at` attribute approach for scheduling, and a `PATCH /campaign-send-jobs/{id}` (or cancel job) approach for cancellation. The spec (§5 K2) explicitly requires Plan K2 to confirm the current endpoint **for the configured revision** before building `schedule.py` and `cancel.py`. This task records the finding so Tasks 5 and 6 implement against verified reality, not a guess.

**Files:**
- Create: `docs/superpowers/notes/klaviyo-send-endpoint.md`

- [ ] **Step 1: Identify the revision in play.** Read the dated revision the toolkit defaults to:

```bash
uv run python -c "from klaviyo.utils.client import _DEFAULT_REVISION; print(_DEFAULT_REVISION)"
grep -n "klaviyo" store-config.example.yaml
```
Record both the `_DEFAULT_REVISION` constant and the `domains.klaviyo.api_version` example value. The schedule/cancel implementation must be correct for whichever revision a user is on (default + example).

- [ ] **Step 2: Look up the current endpoint (Shopify-style docs lookup).** Use the same documentation-lookup posture the Shopify scripts use against `shopify.dev` — but pointed at Klaviyo's API reference. Check Klaviyo's "Campaigns API" reference for the **Send Job** / **scheduling** operations at the recorded revision. Confirm three things and write them down:
  1. **Schedule endpoint & body:** Is it `POST /api/campaign-send-jobs` with a `campaign-send-job` resource referencing the campaign (+ a `scheduled_at` / `send_strategy`)? Or is scheduling expressed by `PATCH /api/campaigns/{id}` with a `send_strategy`/`scheduled_at` attribute? Capture the exact path, JSON:API `type`, and required attributes.
  2. **Send-now path:** whether an immediate send uses the same job resource with no `scheduled_at` (or `send_strategy: "immediate"`) — note it; `schedule.py` will support both scheduled and immediate sends.
  3. **Cancel endpoint & body:** Is cancellation `PATCH /api/campaign-send-jobs/{id}` with `action: "cancel"` (or `"revert"`)? Or `DELETE` of the job? Capture the exact path, `type`, and action attribute values.

  If web/docs tools are unavailable in the execution environment, fall back to a `--dry-run`-only verification: query a real campaign's relationships via `campaigns/get.py` against a dev account (gated by `KLAVIYO_INTEGRATION_TESTS=1`) and inspect the `links`/`relationships` to derive the job resource path. Do **not** proceed to live code paths in Tasks 5/6 until the path is confirmed by one of these means.

- [ ] **Step 3: Record the finding.** Write `docs/superpowers/notes/klaviyo-send-endpoint.md` containing: the revision checked, the confirmed schedule endpoint + body shape, the send-now variation, the confirmed cancel endpoint + body shape, and a dated source link/citation. Tasks 5 and 6 must match this note exactly; if the note later changes, those scripts and their tests change with it.

> The code blocks in Tasks 5 and 6 below assume the **`campaign-send-jobs` resource** shape (schedule = `POST /campaign-send-jobs`; cancel = `PATCH /campaign-send-jobs/{id}` with `{"attributes": {"action": "cancel"}}`), which is the established shape for recent dated revisions. **If Task 4 finds otherwise for the configured revision, adjust the path/`type`/attributes (and the matching test assertions) in Tasks 5/6 to match the note before implementing.** The script *structure* (flags, `--dry-run`, `--yes` gate, `check_errors`) does not change either way.

- [ ] **Step 4: Commit the note.**

```bash
mkdir -p docs/superpowers/notes
git add docs/superpowers/notes/klaviyo-send-endpoint.md
git commit -m "docs(klaviyo): verify campaign send/cancel endpoint for configured revision"
```

---

## Task 5: `campaigns/schedule.py` (gated; endpoint per Task 4)

Schedule (or immediately send) a campaign. **Highest stakes in the domain** — `--yes`-gated; `--dry-run` works without `--yes` and prints the body without calling the API. Implement against the endpoint confirmed in Task 4; the code below assumes the `campaign-send-jobs` resource shape — reconcile with `docs/superpowers/notes/klaviyo-send-endpoint.md` before writing.

**Files:**
- Create: `klaviyo/scripts/campaigns/schedule.py`
- Create: `tests/klaviyo/scripts/test_campaigns_schedule.py`

- [ ] **Step 1: Reconcile with Task 4's note.** Open `docs/superpowers/notes/klaviyo-send-endpoint.md`. If the confirmed schedule path/`type`/attributes differ from the assumed `campaign-send-jobs` shape below, edit the test assertions and the `_build_body`/`post` call in Step 3 to match before continuing.

- [ ] **Step 2: Write failing test.** Write `tests/klaviyo/scripts/test_campaigns_schedule.py` (assumes the `campaign-send-jobs` shape; adjust per the note):

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.campaigns import schedule as schedcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.campaigns.schedule.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.campaigns.schedule.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_schedule_dry_run_prints_body_without_yes(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "schedule.py",
                "--id",
                "CMP1",
                "--at",
                "2026-06-01T09:00:00",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert schedcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "campaign-send-job"
    assert parsed["data"]["id"] == "CMP1"
    assert parsed["data"]["attributes"]["scheduled_at"] == "2026-06-01T09:00:00"


def test_schedule_without_yes_errors_in_live_mode(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["schedule.py", "--id", "CMP1", "--at", "2026-06-01T09:00:00"]
        ):
            try:
                rc = schedcmd.main()
            except SystemExit as e:
                rc = e.code
        assert rc != 0
        assert client.post.call_count == 0


def test_schedule_with_yes_posts_send_job(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"data": {"id": "CMP1", "type": "campaign-send-job"}}
        with patch.object(
            sys, "argv", ["schedule.py", "--id", "CMP1", "--at", "2026-06-01T09:00:00", "--yes"]
        ):
            assert schedcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "campaign-send-jobs"
        body = kwargs.get("json") or args[1]
        assert body["data"]["attributes"]["scheduled_at"] == "2026-06-01T09:00:00"


def test_schedule_send_now_omits_scheduled_at(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["schedule.py", "--id", "CMP1", "--send-now", "--dry-run", "--output", "json"],
        ):
            assert schedcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert "scheduled_at" not in parsed["data"]["attributes"]
```

- [ ] **Step 3: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_campaigns_schedule.py -v
```

- [ ] **Step 4: Implement `klaviyo/scripts/campaigns/schedule.py`.** Complete code (assumes the `campaign-send-jobs` shape — reconcile with the Task 4 note first):

```python
"""Schedule or immediately send a Klaviyo campaign.

Highest-stakes operation in the domain: --yes is required for live execution.
--dry-run works without --yes and prints the request body without calling the
API. The exact send-job endpoint/shape is verified per-revision in
docs/superpowers/notes/klaviyo-send-endpoint.md (Plan K2 Task 4).
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
    if not args.send_now:
        attributes["scheduled_at"] = args.at
    return {
        "data": {
            "type": "campaign-send-job",
            "id": args.id,
            "attributes": attributes,
        }
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Schedule or send a Klaviyo campaign.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Campaign id")
    parser.add_argument("--at", help="ISO-8601 scheduled send time (required unless --send-now)")
    parser.add_argument(
        "--send-now",
        dest="send_now",
        action="store_true",
        help="Send immediately instead of scheduling",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if not args.send_now and not args.at:
        parser.error("one of --at or --send-now is required")

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    if not args.yes:
        parser.error("--yes is required to confirm scheduling/sending a campaign; aborting")

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("campaign-send-jobs", json=body)

    check_errors(result)
    when = "now" if args.send_now else args.at
    print(f"Scheduled campaign {args.id} to send {when}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_campaigns_schedule.py -v
uv run ruff check klaviyo/scripts/campaigns/schedule.py tests/klaviyo/scripts/test_campaigns_schedule.py
uv run ruff format klaviyo/scripts/campaigns/schedule.py tests/klaviyo/scripts/test_campaigns_schedule.py
git add klaviyo/scripts/campaigns/schedule.py tests/klaviyo/scripts/test_campaigns_schedule.py
git commit -m "feat(klaviyo): campaigns/schedule.py gated on --yes (endpoint per Task 4)"
```

---

## Task 6: `campaigns/cancel.py` (gated; endpoint per Task 4)

Cancel/revert a scheduled send. `--yes`-gated; `--dry-run` works without `--yes`. Implement against the cancel endpoint confirmed in Task 4; the code below assumes `PATCH /campaign-send-jobs/{id}` with `{"attributes": {"action": "cancel"}}` — reconcile with the note first.

**Files:**
- Create: `klaviyo/scripts/campaigns/cancel.py`
- Create: `tests/klaviyo/scripts/test_campaigns_cancel.py`

- [ ] **Step 1: Reconcile with Task 4's note.** Open `docs/superpowers/notes/klaviyo-send-endpoint.md`. If the confirmed cancel path/`type`/action differs from the assumed `PATCH /campaign-send-jobs/{id}` + `action: "cancel"` shape, adjust the test assertions and the `client.patch` call below to match before continuing.

- [ ] **Step 2: Write failing test.** Write `tests/klaviyo/scripts/test_campaigns_cancel.py` (assumes the PATCH-action shape; adjust per the note):

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.campaigns import cancel as cancelcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.campaigns.cancel.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.campaigns.cancel.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_cancel_dry_run_prints_body_without_yes(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["cancel.py", "--id", "CMP1", "--dry-run", "--output", "json"]
        ):
            assert cancelcmd.main() == 0
        assert client.patch.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "campaign-send-job"
    assert parsed["data"]["id"] == "CMP1"
    assert parsed["data"]["attributes"]["action"] == "cancel"


def test_cancel_without_yes_errors_in_live_mode(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(sys, "argv", ["cancel.py", "--id", "CMP1"]):
            try:
                rc = cancelcmd.main()
            except SystemExit as e:
                rc = e.code
        assert rc != 0
        assert client.patch.call_count == 0


def test_cancel_with_yes_patches_send_job(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.patch.return_value = {"data": {"id": "CMP1", "type": "campaign-send-job"}}
        with patch.object(sys, "argv", ["cancel.py", "--id", "CMP1", "--yes"]):
            assert cancelcmd.main() == 0
        args, kwargs = client.patch.call_args
        assert args[0] == "campaign-send-jobs/CMP1"
        body = kwargs.get("json") or args[1]
        assert body["data"]["attributes"]["action"] == "cancel"
```

- [ ] **Step 3: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_campaigns_cancel.py -v
```

- [ ] **Step 4: Implement `klaviyo/scripts/campaigns/cancel.py`.** Complete code (assumes the PATCH-action shape — reconcile with the Task 4 note first):

```python
"""Cancel a scheduled Klaviyo campaign send.

High-stakes: --yes is required for live execution. --dry-run works without
--yes and prints the request body without calling the API. The exact cancel
endpoint/shape is verified per-revision in
docs/superpowers/notes/klaviyo-send-endpoint.md (Plan K2 Task 4).
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
            "type": "campaign-send-job",
            "id": args.id,
            "attributes": {"action": "cancel"},
        }
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cancel a scheduled Klaviyo campaign send.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Campaign id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    if not args.yes:
        parser.error("--yes is required to confirm cancelling a campaign send; aborting")

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.patch(f"campaign-send-jobs/{args.id}", json=body)

    check_errors(result)
    print(f"Cancelled send for campaign {args.id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_campaigns_cancel.py -v
uv run ruff check klaviyo/scripts/campaigns/cancel.py tests/klaviyo/scripts/test_campaigns_cancel.py
uv run ruff format klaviyo/scripts/campaigns/cancel.py tests/klaviyo/scripts/test_campaigns_cancel.py
git add klaviyo/scripts/campaigns/cancel.py tests/klaviyo/scripts/test_campaigns_cancel.py
git commit -m "feat(klaviyo): campaigns/cancel.py gated on --yes (endpoint per Task 4)"
```

---

## Task 7: `campaigns/delete.py` (gated)

`DELETE /campaigns/{id}`. `--yes`-gated; `--dry-run` works without `--yes`. Mirrors `lists/delete.py` from K1 exactly.

**Files:**
- Create: `klaviyo/scripts/campaigns/delete.py`
- Create: `tests/klaviyo/scripts/test_campaigns_delete.py`

- [ ] **Step 1: Write failing test.** Write `tests/klaviyo/scripts/test_campaigns_delete.py`:

```python
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.campaigns import delete as deletecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.campaigns.delete.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.campaigns.delete.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_delete_dry_run_skips_call_without_yes(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(sys, "argv", ["delete.py", "--id", "CMP1", "--dry-run"]):
            assert deletecmd.main() == 0
        assert client.delete.call_count == 0
    assert "CMP1" in capsys.readouterr().out


def test_delete_without_yes_errors(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(sys, "argv", ["delete.py", "--id", "CMP1"]):
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
        with patch.object(sys, "argv", ["delete.py", "--id", "CMP1", "--yes"]):
            assert deletecmd.main() == 0
        client.delete.assert_called_once_with("campaigns/CMP1")
    assert "Deleted: CMP1" in capsys.readouterr().out
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_campaigns_delete.py -v
```

- [ ] **Step 3: Implement `klaviyo/scripts/campaigns/delete.py`.** Complete code:

```python
"""Delete a Klaviyo campaign by id.

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
    parser = argparse.ArgumentParser(description="Delete a Klaviyo campaign by id.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Campaign id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if args.dry_run:
        print(f"Would delete campaign {args.id}")
        return 0

    if not args.yes:
        parser.error("--yes is required to confirm deletion; aborting")

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.delete(f"campaigns/{args.id}")

    check_errors(result)
    print(f"Deleted: {args.id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_campaigns_delete.py -v
uv run ruff check klaviyo/scripts/campaigns/delete.py tests/klaviyo/scripts/test_campaigns_delete.py
uv run ruff format klaviyo/scripts/campaigns/delete.py tests/klaviyo/scripts/test_campaigns_delete.py
git add klaviyo/scripts/campaigns/delete.py tests/klaviyo/scripts/test_campaigns_delete.py
git commit -m "feat(klaviyo): campaigns/delete.py gated on --yes"
```

---

## Task 8: `templates/list.py` and `templates/get.py`

`GET /templates` and `GET /templates/{id}`. Read-only; flatten resources. Same shape as K1's `lists/list.py`/`lists/get.py` (without `--with-members`).

**Files:**
- Create: `klaviyo/scripts/templates/__init__.py`
- Create: `klaviyo/scripts/templates/list.py`
- Create: `klaviyo/scripts/templates/get.py`
- Create: `tests/klaviyo/scripts/test_templates_list.py`
- Create: `tests/klaviyo/scripts/test_templates_get.py`

- [ ] **Step 1: Create the templates package marker.**

```bash
mkdir -p klaviyo/scripts/templates
touch klaviyo/scripts/templates/__init__.py
```

- [ ] **Step 2: Write failing tests.** Write `tests/klaviyo/scripts/test_templates_list.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.templates import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.templates.list.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.templates.list.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_templates_list_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [{"id": "TPL1", "type": "template", "attributes": {"name": "Welcome"}}]
        )
        with patch.object(sys, "argv", ["list.py", "--output", "json"]):
            assert listcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "TPL1"
    assert parsed[0]["name"] == "Welcome"
```

Write `tests/klaviyo/scripts/test_templates_get.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.templates import get as getcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.templates.get.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.templates.get.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_get_template_by_id(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "data": {"id": "TPL1", "type": "template", "attributes": {"name": "Welcome"}}
        }
        with patch.object(sys, "argv", ["get.py", "--id", "TPL1", "--output", "json"]):
            assert getcmd.main() == 0
        client.get.assert_called_once_with("templates/TPL1")
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "TPL1"
    assert parsed["name"] == "Welcome"
```

- [ ] **Step 3: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_templates_list.py tests/klaviyo/scripts/test_templates_get.py -v
```

- [ ] **Step 4: Implement `klaviyo/scripts/templates/list.py`.** Complete code:

```python
"""List Klaviyo email templates.

Flattens JSON:API template resources into flat rows. Honors --limit via cursor
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
        "editor_type": attrs.get("editor_type"),
        "created": attrs.get("created"),
        "updated": attrs.get("updated"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Klaviyo email templates.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        rows = [_flatten(r) for r in client.paginate("templates", limit=args.limit)]

    print(format_output(rows, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Implement `klaviyo/scripts/templates/get.py`.** Complete code:

```python
"""Get a Klaviyo email template by id (includes rendered html/text attributes)."""

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


def _flatten(resource: dict) -> dict:
    attrs = resource.get("attributes") or {}
    return {
        "id": resource.get("id"),
        "name": attrs.get("name"),
        "editor_type": attrs.get("editor_type"),
        "html": attrs.get("html"),
        "text": attrs.get("text"),
        "created": attrs.get("created"),
        "updated": attrs.get("updated"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get a Klaviyo email template by id.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Template id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        body = client.get(f"templates/{args.id}")
        check_errors(body)
        resource = body.get("data") or {}

    print(format_output(_flatten(resource), args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_templates_list.py tests/klaviyo/scripts/test_templates_get.py -v
uv run ruff check klaviyo/scripts/templates/ tests/klaviyo/scripts/test_templates_list.py tests/klaviyo/scripts/test_templates_get.py
uv run ruff format klaviyo/scripts/templates/ tests/klaviyo/scripts/test_templates_list.py tests/klaviyo/scripts/test_templates_get.py
git add klaviyo/scripts/templates/__init__.py klaviyo/scripts/templates/list.py klaviyo/scripts/templates/get.py tests/klaviyo/scripts/test_templates_list.py tests/klaviyo/scripts/test_templates_get.py
git commit -m "feat(klaviyo): templates/list.py and templates/get.py"
```

---

## Task 9: `templates/create.py` and `templates/update.py`

`POST /templates` and `PATCH /templates/{id}`. Build a JSON:API `template` resource (name + html, optional text). `--dry-run` on both; update carries the `id` inside `data`. Reads the HTML body from a file via `--html-file` (CLI args are a poor place for full HTML).

**Files:**
- Create: `klaviyo/scripts/templates/create.py`
- Create: `klaviyo/scripts/templates/update.py`
- Create: `tests/klaviyo/scripts/test_templates_create.py`
- Create: `tests/klaviyo/scripts/test_templates_update.py`

- [ ] **Step 1: Write failing tests.** Write `tests/klaviyo/scripts/test_templates_create.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.templates import create as createcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.templates.create.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.templates.create.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_create_template_dry_run_with_inline_html(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["create.py", "--name", "Welcome", "--html", "<h1>Hi</h1>", "--dry-run", "--output", "json"],
        ):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "template"
    assert parsed["data"]["attributes"]["name"] == "Welcome"
    assert parsed["data"]["attributes"]["html"] == "<h1>Hi</h1>"


def test_create_template_reads_html_file(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    html_file = tmp_path / "t.html"
    html_file.write_text("<p>from file</p>")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["create.py", "--name", "Welcome", "--html-file", str(html_file), "--dry-run", "--output", "json"],
        ):
            assert createcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["attributes"]["html"] == "<p>from file</p>"


def test_create_template_posts(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {
            "data": {"id": "TPL9", "type": "template", "attributes": {"name": "Welcome"}}
        }
        with patch.object(sys, "argv", ["create.py", "--name", "Welcome", "--html", "<h1>Hi</h1>"]):
            assert createcmd.main() == 0
        args, _ = client.post.call_args
        assert args[0] == "templates"
```

Write `tests/klaviyo/scripts/test_templates_update.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.templates import update as updatecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.templates.update.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.templates.update.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_update_template_dry_run_includes_id(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["update.py", "--id", "TPL1", "--name", "Welcome v2", "--dry-run", "--output", "json"],
        ):
            assert updatecmd.main() == 0
        assert client.patch.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["id"] == "TPL1"
    assert parsed["data"]["type"] == "template"
    assert parsed["data"]["attributes"]["name"] == "Welcome v2"


def test_update_template_patches_path(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.patch.return_value = {
            "data": {"id": "TPL1", "type": "template", "attributes": {"name": "Welcome v2"}}
        }
        with patch.object(sys, "argv", ["update.py", "--id", "TPL1", "--name", "Welcome v2"]):
            assert updatecmd.main() == 0
        args, _ = client.patch.call_args
        assert args[0] == "templates/TPL1"
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_templates_create.py tests/klaviyo/scripts/test_templates_update.py -v
```

- [ ] **Step 3: Implement `klaviyo/scripts/templates/create.py`.** Complete code:

```python
"""Create a Klaviyo email template.

HTML comes from --html (inline) or --html-file (path). --dry-run prints the
request body and skips the POST.
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


def _resolve_html(args: argparse.Namespace) -> str:
    if args.html is not None:
        return args.html
    return Path(args.html_file).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a Klaviyo email template.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--name", required=True, help="Template name")
    parser.add_argument("--html", help="Inline HTML body")
    parser.add_argument("--html-file", dest="html_file", help="Path to an HTML file")
    parser.add_argument("--text", help="Optional plain-text body")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if not args.html and not args.html_file:
        parser.error("one of --html or --html-file is required")

    attributes: dict[str, object] = {"name": args.name, "html": _resolve_html(args)}
    if args.text:
        attributes["text"] = args.text
    body = {"data": {"type": "template", "attributes": attributes}}

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("templates", json=body)

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

- [ ] **Step 4: Implement `klaviyo/scripts/templates/update.py`.** Complete code:

```python
"""Update a Klaviyo email template by id.

JSON:API update bodies carry the resource id inside ``data``. HTML may be
supplied via --html or --html-file. --dry-run prints the body and skips the
PATCH.
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
    if args.name:
        attributes["name"] = args.name
    if args.html is not None:
        attributes["html"] = args.html
    elif args.html_file:
        attributes["html"] = Path(args.html_file).read_text(encoding="utf-8")
    if args.text:
        attributes["text"] = args.text
    return {"data": {"type": "template", "id": args.id, "attributes": attributes}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update a Klaviyo email template by id.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Template id")
    parser.add_argument("--name", help="New template name")
    parser.add_argument("--html", help="Inline HTML body")
    parser.add_argument("--html-file", dest="html_file", help="Path to an HTML file")
    parser.add_argument("--text", help="Plain-text body")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = _build_body(args)

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.patch(f"templates/{args.id}", json=body)

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
uv run pytest tests/klaviyo/scripts/test_templates_create.py tests/klaviyo/scripts/test_templates_update.py -v
uv run ruff check klaviyo/scripts/templates/create.py klaviyo/scripts/templates/update.py tests/klaviyo/scripts/test_templates_create.py tests/klaviyo/scripts/test_templates_update.py
uv run ruff format klaviyo/scripts/templates/create.py klaviyo/scripts/templates/update.py tests/klaviyo/scripts/test_templates_create.py tests/klaviyo/scripts/test_templates_update.py
git add klaviyo/scripts/templates/create.py klaviyo/scripts/templates/update.py tests/klaviyo/scripts/test_templates_create.py tests/klaviyo/scripts/test_templates_update.py
git commit -m "feat(klaviyo): templates/create.py and templates/update.py with --dry-run"
```

---

## Task 10: `templates/delete.py` (gated)

`DELETE /templates/{id}`. `--yes`-gated; `--dry-run` works without `--yes`. Mirrors `campaigns/delete.py`.

**Files:**
- Create: `klaviyo/scripts/templates/delete.py`
- Create: `tests/klaviyo/scripts/test_templates_delete.py`

- [ ] **Step 1: Write failing test.** Write `tests/klaviyo/scripts/test_templates_delete.py`:

```python
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.templates import delete as deletecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.templates.delete.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.templates.delete.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_delete_dry_run_skips_call_without_yes(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(sys, "argv", ["delete.py", "--id", "TPL1", "--dry-run"]):
            assert deletecmd.main() == 0
        assert client.delete.call_count == 0
    assert "TPL1" in capsys.readouterr().out


def test_delete_without_yes_errors(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(sys, "argv", ["delete.py", "--id", "TPL1"]):
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
        with patch.object(sys, "argv", ["delete.py", "--id", "TPL1", "--yes"]):
            assert deletecmd.main() == 0
        client.delete.assert_called_once_with("templates/TPL1")
    assert "Deleted: TPL1" in capsys.readouterr().out
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_templates_delete.py -v
```

- [ ] **Step 3: Implement `klaviyo/scripts/templates/delete.py`.** Complete code:

```python
"""Delete a Klaviyo email template by id.

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
    parser = argparse.ArgumentParser(description="Delete a Klaviyo email template by id.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Template id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if args.dry_run:
        print(f"Would delete template {args.id}")
        return 0

    if not args.yes:
        parser.error("--yes is required to confirm deletion; aborting")

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.delete(f"templates/{args.id}")

    check_errors(result)
    print(f"Deleted: {args.id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_templates_delete.py -v
uv run ruff check klaviyo/scripts/templates/delete.py tests/klaviyo/scripts/test_templates_delete.py
uv run ruff format klaviyo/scripts/templates/delete.py tests/klaviyo/scripts/test_templates_delete.py
git add klaviyo/scripts/templates/delete.py tests/klaviyo/scripts/test_templates_delete.py
git commit -m "feat(klaviyo): templates/delete.py gated on --yes"
```

---

## Task 11: `templates/render.py` and `templates/clone.py`

`POST /template-render` (render a template with context) and `POST /template-clone` (copy an existing template). Both are mutations with `--dry-run`; neither is destructive, so neither is `--yes`-gated. Render context comes from `--context-file` (a JSON file) or `--context` (inline JSON string).

**Files:**
- Create: `klaviyo/scripts/templates/render.py`
- Create: `klaviyo/scripts/templates/clone.py`
- Create: `tests/klaviyo/scripts/test_templates_render.py`
- Create: `tests/klaviyo/scripts/test_templates_clone.py`

- [ ] **Step 1: Write failing tests.** Write `tests/klaviyo/scripts/test_templates_render.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.templates import render as rendercmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.templates.render.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.templates.render.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_render_dry_run_builds_body(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["render.py", "--id", "TPL1", "--context", '{"first_name": "Ada"}', "--dry-run", "--output", "json"],
        ):
            assert rendercmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "template"
    assert parsed["data"]["id"] == "TPL1"
    assert parsed["data"]["attributes"]["context"] == {"first_name": "Ada"}


def test_render_posts_to_template_render(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {
            "data": {"id": "TPL1", "type": "template", "attributes": {"html": "<h1>Hi Ada</h1>"}}
        }
        with patch.object(
            sys, "argv", ["render.py", "--id", "TPL1", "--context", '{"first_name": "Ada"}']
        ):
            assert rendercmd.main() == 0
        args, _ = client.post.call_args
        assert args[0] == "template-render"
```

Write `tests/klaviyo/scripts/test_templates_clone.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.templates import clone as clonecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.templates.clone.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.templates.clone.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_clone_dry_run_builds_body(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["clone.py", "--id", "TPL1", "--name", "Welcome (copy)", "--dry-run", "--output", "json"],
        ):
            assert clonecmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "template"
    assert parsed["data"]["id"] == "TPL1"
    assert parsed["data"]["attributes"]["name"] == "Welcome (copy)"


def test_clone_posts_to_template_clone(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {
            "data": {"id": "TPL2", "type": "template", "attributes": {"name": "Welcome (copy)"}}
        }
        with patch.object(sys, "argv", ["clone.py", "--id", "TPL1", "--name", "Welcome (copy)"]):
            assert clonecmd.main() == 0
        args, _ = client.post.call_args
        assert args[0] == "template-clone"
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_templates_render.py tests/klaviyo/scripts/test_templates_clone.py -v
```

- [ ] **Step 3: Implement `klaviyo/scripts/templates/render.py`.** Complete code:

```python
"""Render a Klaviyo email template with a template context.

Context comes from --context (inline JSON string) or --context-file (path to a
JSON file). --dry-run prints the request body and skips the POST.
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


def _resolve_context(args: argparse.Namespace) -> dict:
    if args.context is not None:
        return json.loads(args.context)
    if args.context_file:
        return json.loads(Path(args.context_file).read_text(encoding="utf-8"))
    return {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a Klaviyo template with context.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Template id")
    parser.add_argument("--context", help="Inline JSON template context")
    parser.add_argument("--context-file", dest="context_file", help="Path to a JSON context file")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    context = _resolve_context(args)
    body = {
        "data": {
            "type": "template",
            "id": args.id,
            "attributes": {"context": context},
        }
    }

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("template-render", json=body)

    check_errors(result)
    attrs = (result.get("data") or {}).get("attributes") or {}
    print(format_output({"html": attrs.get("html"), "text": attrs.get("text")}, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Implement `klaviyo/scripts/templates/clone.py`.** Complete code:

```python
"""Clone an existing Klaviyo email template.

Builds a JSON:API template resource referencing the source id plus the new
clone's name. --dry-run prints the request body and skips the POST.
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
    parser = argparse.ArgumentParser(description="Clone a Klaviyo email template.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--id", required=True, help="Source template id")
    parser.add_argument("--name", required=True, help="Name for the cloned template")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = {
        "data": {
            "type": "template",
            "id": args.id,
            "attributes": {"name": args.name},
        }
    }

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("template-clone", json=body)

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
uv run pytest tests/klaviyo/scripts/test_templates_render.py tests/klaviyo/scripts/test_templates_clone.py -v
uv run ruff check klaviyo/scripts/templates/render.py klaviyo/scripts/templates/clone.py tests/klaviyo/scripts/test_templates_render.py tests/klaviyo/scripts/test_templates_clone.py
uv run ruff format klaviyo/scripts/templates/render.py klaviyo/scripts/templates/clone.py tests/klaviyo/scripts/test_templates_render.py tests/klaviyo/scripts/test_templates_clone.py
git add klaviyo/scripts/templates/render.py klaviyo/scripts/templates/clone.py tests/klaviyo/scripts/test_templates_render.py tests/klaviyo/scripts/test_templates_clone.py
git commit -m "feat(klaviyo): templates/render.py and templates/clone.py with --dry-run"
```

---

## Task 12: `templates/assign.py`

`POST /campaign-message-assign-template`. Assigns a template to a campaign message (the wiring step between a created campaign's message and a template). Mutation with `--dry-run`; not destructive, so not `--yes`-gated.

**Files:**
- Create: `klaviyo/scripts/templates/assign.py`
- Create: `tests/klaviyo/scripts/test_templates_assign.py`

- [ ] **Step 1: Write failing test.** Write `tests/klaviyo/scripts/test_templates_assign.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.templates import assign as assigncmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.templates.assign.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.templates.assign.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_assign_dry_run_builds_body(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["assign.py", "--message-id", "MSG1", "--template-id", "TPL1", "--dry-run", "--output", "json"],
        ):
            assert assigncmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "campaign-message"
    assert parsed["data"]["id"] == "MSG1"
    rel = parsed["data"]["relationships"]["template"]["data"]
    assert rel["type"] == "template"
    assert rel["id"] == "TPL1"


def test_assign_posts_to_endpoint(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"data": {"id": "MSG1", "type": "campaign-message"}}
        with patch.object(
            sys, "argv", ["assign.py", "--message-id", "MSG1", "--template-id", "TPL1"]
        ):
            assert assigncmd.main() == 0
        args, _ = client.post.call_args
        assert args[0] == "campaign-message-assign-template"
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/klaviyo/scripts/test_templates_assign.py -v
```

- [ ] **Step 3: Implement `klaviyo/scripts/templates/assign.py`.** Complete code:

```python
"""Assign a template to a Klaviyo campaign message.

Wires an existing template to a campaign's message. --dry-run prints the
request body and skips the POST.
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
    parser = argparse.ArgumentParser(description="Assign a template to a campaign message.")
    add_common_flags(parser)
    add_klaviyo_flags(parser)
    parser.add_argument("--message-id", dest="message_id", required=True, help="Campaign message id")
    parser.add_argument("--template-id", dest="template_id", required=True, help="Template id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    body = {
        "data": {
            "type": "campaign-message",
            "id": args.message_id,
            "relationships": {
                "template": {"data": {"type": "template", "id": args.template_id}}
            },
        }
    }

    if args.dry_run:
        print(format_output(body, args.output))
        return 0

    cfg = load_config(args.config)
    with KlaviyoClient(config=cfg, revision=args.revision) as client:
        result = client.post("campaign-message-assign-template", json=body)

    check_errors(result)
    print(f"Assigned template {args.template_id} to message {args.message_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/klaviyo/scripts/test_templates_assign.py -v
uv run ruff check klaviyo/scripts/templates/assign.py tests/klaviyo/scripts/test_templates_assign.py
uv run ruff format klaviyo/scripts/templates/assign.py tests/klaviyo/scripts/test_templates_assign.py
git add klaviyo/scripts/templates/assign.py tests/klaviyo/scripts/test_templates_assign.py
git commit -m "feat(klaviyo): templates/assign.py with --dry-run"
```

---

## Task 13: Skills — `klaviyo-campaigns` and `klaviyo-templates`

**Files:**
- Create: `skills/klaviyo-campaigns/SKILL.md`
- Create: `skills/klaviyo-templates/SKILL.md`

Mirror the K1 skill shape (and `skills/shopify-webhooks/SKILL.md`): a `name:` line and a single-paragraph `description:` packed with trigger phrases and the per-script flag posture, then a body covering when to use, each script, and a "defer to direct API use" note for unsupported ops.

- [ ] **Step 1: Write `skills/klaviyo-campaigns/SKILL.md`.** Covers `campaigns/{list,get,create,schedule,cancel,delete}`. Front-matter `description` must name triggers: "list campaigns", "show a campaign", "create a campaign", "schedule a campaign", "send a campaign now", "cancel a scheduled send", "delete a campaign". Note `--dry-run` on create/schedule/cancel; note `--yes` gates `schedule`, `cancel`, and `delete` (schedule is the highest-stakes op). Note that the send/cancel endpoint is revision-sensitive and was verified in `docs/superpowers/notes/klaviyo-send-endpoint.md`; multi-message campaigns are deferred to direct API use.

- [ ] **Step 2: Write `skills/klaviyo-templates/SKILL.md`.** Covers `templates/{list,get,create,update,delete,render,clone,assign}`. Triggers: "list templates", "show a template", "create a template", "update a template", "delete a template", "render a template", "clone a template", "assign a template to a campaign". Note `--dry-run` on all mutations and `--yes` only on `delete`; note HTML is supplied via `--html`/`--html-file` and render/assign context via JSON.

- [ ] **Step 3: Commit.**

```bash
git add skills/klaviyo-campaigns/SKILL.md skills/klaviyo-templates/SKILL.md
git commit -m "docs(klaviyo): klaviyo-campaigns and klaviyo-templates skills"
```

---

## Task 14: Full sweep, CHANGELOG, smoke

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Full suite + ruff (with the klaviyo extra installed).**

```bash
uv sync --extra dev --extra shopify --extra webhooks --extra klaviyo
uv run pytest tests/ --ignore=tests/shopify/test_whoami_integration.py -v
uv run ruff check .
uv run ruff format --check .
```
Expected: all green; the new `tests/klaviyo/scripts/test_campaigns_*.py` and `test_templates_*.py` are collected and pass; K1 and Shopify tests unaffected.

- [ ] **Step 2: Smoke each script's `--help` and a representative `--dry-run`.**

```bash
uv run klaviyo/scripts/campaigns/list.py --help
uv run klaviyo/scripts/campaigns/create.py --name "Spring" --list-id LST1 --subject "Hi" --from-email a@b.com --from-label Shop --dry-run --output json
uv run klaviyo/scripts/campaigns/schedule.py --id CMP1 --at 2026-06-01T09:00:00 --dry-run --output json
uv run klaviyo/scripts/campaigns/cancel.py --id CMP1 --dry-run --output json
uv run klaviyo/scripts/campaigns/delete.py --id CMP1 --dry-run
uv run klaviyo/scripts/templates/create.py --name Welcome --html "<h1>Hi</h1>" --dry-run --output json
uv run klaviyo/scripts/templates/delete.py --id TPL1 --dry-run
uv run klaviyo/scripts/templates/render.py --id TPL1 --context '{"first_name":"Ada"}' --dry-run --output json
uv run klaviyo/scripts/templates/assign.py --message-id MSG1 --template-id TPL1 --dry-run --output json
```
Expected: help text prints; `--dry-run` prints the JSON:API body / intent and exits 0 without needing a real API key or `--yes`.

- [ ] **Step 3: Update `CHANGELOG.md`.** Add an entry under a new version heading (bump from K1's line; e.g. `## [0.7.0] — 2026-05-29`) noting: Klaviyo sending cluster — campaigns (`list/get/create/schedule/cancel/delete`) and templates (`list/get/create/update/delete/render/clone/assign`) with `--dry-run` on mutations and `--yes` gating `schedule`/`cancel`/`campaigns delete`/`templates delete`; note the send/cancel endpoint was verified per-revision (`docs/superpowers/notes/klaviyo-send-endpoint.md`).

- [ ] **Step 4: Commit.**

```bash
git add CHANGELOG.md
git commit -m "docs(klaviyo): CHANGELOG for Klaviyo sending (K2)"
```

---

## Definition of Done

(Scoped to K2, per spec §11/§12.)

- [ ] Sending cluster per spec §5 K2: `campaigns/{list,get,create,schedule,cancel,delete}` and `templates/{list,get,create,update,delete,render,clone,assign}` all implemented and runnable (`--help` works for each).
- [ ] `campaigns/list.py` always sends the mandatory `messages.channel` filter (default `email`, `--channel` override).
- [ ] The campaign send/cancel endpoint was **verified against the configured Klaviyo revision before building** (Task 4), with the finding recorded in `docs/superpowers/notes/klaviyo-send-endpoint.md`; `schedule.py` and `cancel.py` (and their tests) match that note rather than a hard-coded guess.
- [ ] `--dry-run` on every mutation prints the JSON:API body and skips the call; `--yes` gates `campaigns/schedule`, `campaigns/cancel`, `campaigns/delete`, and `templates/delete` (errors via `parser.error` before any network call when missing in live mode).
- [ ] Per-script unit tests green, mocking `KlaviyoClient` (no live calls); integration tests, if added, gated by `KLAVIYO_INTEGRATION_TESTS=1` and skipped by default.
- [ ] `templates/create.py`/`update.py` accept HTML via `--html` or `--html-file`; `templates/render.py` accepts context via `--context`/`--context-file`.
- [ ] `klaviyo-campaigns` and `klaviyo-templates` skills present and cover their clusters, including the deferred multi-message-campaign note and the send-endpoint caveat.
- [ ] Full `uv run pytest tests/` green; `ruff check .` and `ruff format --check .` clean. CHANGELOG bumped.
