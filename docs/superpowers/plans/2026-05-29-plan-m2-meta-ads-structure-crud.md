# Plan M2: Meta Ads Structure CRUD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Meta Ads structure-write cluster — `campaigns/`, `adsets/`, `ads/` create/update/pause/activate/delete plus `creatives/create` — so a Meta (Facebook/Instagram) Ads account's structure can be managed from `uv run meta_ads/scripts/<cluster>/<op>.py` without any path to accidental ad spend.

**Architecture:** All writes go through the existing `MetaClient` (Graph API `POST` for creates/updates, `DELETE` for deletes; built on `core.http.HttpClient`). Every `create` script hard-codes `status=PAUSED` into the form body — there is no flag that yields `ACTIVE`. Activation is a separate `activate.py` per entity, `--yes`-gated; `delete.py` and any budget change on `update.py` are also `--yes`-gated; `--dry-run` on every script prints the Graph node/edge + form params and returns `0` without calling the API.

**Tech Stack:** `httpx>=0.27`, `pyyaml>=6`, `pydantic>=2.7` (the `meta-ads` extra, already populated in M1). Tests use `pytest` with `monkeypatch`/`unittest.mock.patch`. No vendor SDK (`facebook-business`), no MCP.

**Spec reference:** `docs/superpowers/specs/2026-05-29-meta-ads-domain-design.md` §4 (conventions — safe-default create, `--yes` gates), §5 M2 (structure-CRUD script inventory), §6 (data flow), §7 (error handling — gated op without `--yes` → `parser.error` before any network call), §11 (implementation split — Plan M2), §12 (definition of done, scoped here to M2).

**Depends on:** Plan M1 — `meta_ads/utils/client.py` (`MetaClient`, `MetaAPIError`, `account_path`, `check_error`, `_DEFAULT_VERSION`) and `meta_ads/utils/cli.py` (`add_common_flags`, `add_meta_flags` registering `--api-version`/`--yes`, `configure_logging_from_args`, `format_output`) exist and are tested; the `meta-ads` extra, `domains.meta_ads.api_version`, CI wiring, and `META_ACCESS_TOKEN` are in place. No `core/` changes. No new client methods — M1's `MetaClient.post(path, data=...)` and `MetaClient.delete(path, params=...)` cover every write here.

> **Scope note — safe-default `PAUSED` is the load-bearing invariant.** Every `create` script in this plan forces `status=PAUSED` in the request body, and each create test asserts both that `PAUSED` is present **and** that no combination of flags produces `ACTIVE`. The only script that ever sends `status=ACTIVE` is `activate.py`, which is `--yes`-gated. Do not add an `--active`/`--status` flag to any `create` script — that would defeat the guardrail and is explicitly out of scope.

---

## File Structure

| Path | Responsibility |
|---|---|
| `meta_ads/scripts/campaigns/create.py` | `POST /act_<id>/campaigns` — forces `status=PAUSED`; `--objective`, `--name`, special-ad-categories; `--dry-run` |
| `meta_ads/scripts/campaigns/update.py` | `POST /<campaign_id>` — name/budget; budget change `--yes`-gated; `--dry-run` |
| `meta_ads/scripts/campaigns/pause.py` | `POST /<campaign_id>` `status=PAUSED`; `--dry-run` |
| `meta_ads/scripts/campaigns/activate.py` | `POST /<campaign_id>` `status=ACTIVE`; `--dry-run`, `--yes` |
| `meta_ads/scripts/campaigns/delete.py` | `DELETE /<campaign_id>`; `--dry-run`, `--yes` |
| `meta_ads/scripts/adsets/create.py` | `POST /act_<id>/adsets` — forces `status=PAUSED`; campaign/budget/billing/optimization/targeting; `--dry-run` |
| `meta_ads/scripts/adsets/update.py` | `POST /<adset_id>` — name/budget; budget change `--yes`-gated; `--dry-run` |
| `meta_ads/scripts/adsets/pause.py` | `POST /<adset_id>` `status=PAUSED`; `--dry-run` |
| `meta_ads/scripts/adsets/activate.py` | `POST /<adset_id>` `status=ACTIVE`; `--dry-run`, `--yes` |
| `meta_ads/scripts/adsets/delete.py` | `DELETE /<adset_id>`; `--dry-run`, `--yes` |
| `meta_ads/scripts/ads/create.py` | `POST /act_<id>/ads` — forces `status=PAUSED`; adset + creative ref; `--dry-run` |
| `meta_ads/scripts/ads/update.py` | `POST /<ad_id>` — name/creative; `--dry-run` |
| `meta_ads/scripts/ads/pause.py` | `POST /<ad_id>` `status=PAUSED`; `--dry-run` |
| `meta_ads/scripts/ads/activate.py` | `POST /<ad_id>` `status=ACTIVE`; `--dry-run`, `--yes` |
| `meta_ads/scripts/ads/delete.py` | `DELETE /<ad_id>`; `--dry-run`, `--yes` |
| `meta_ads/scripts/creatives/create.py` | `POST /act_<id>/adcreatives` — wires existing image hash / object story spec; `--dry-run` |
| `tests/meta_ads/scripts/test_campaigns_create.py` | asserts `PAUSED` default + no-`ACTIVE` path + `--dry-run` |
| `tests/meta_ads/scripts/test_campaigns_update.py` | asserts budget-change `--yes` gate + `--dry-run` |
| `tests/meta_ads/scripts/test_campaigns_pause.py` | asserts `status=PAUSED` body + `--dry-run` |
| `tests/meta_ads/scripts/test_campaigns_activate.py` | asserts `--yes` gate + `status=ACTIVE` + `--dry-run` |
| `tests/meta_ads/scripts/test_campaigns_delete.py` | asserts `--yes` gate + DELETE + `--dry-run` |
| `tests/meta_ads/scripts/test_adsets_create.py` | asserts `PAUSED` default + no-`ACTIVE` path + `--dry-run` |
| `tests/meta_ads/scripts/test_adsets_activate.py` | asserts `--yes` gate + `status=ACTIVE` + `--dry-run` |
| `tests/meta_ads/scripts/test_adsets_delete.py` | asserts `--yes` gate + DELETE + `--dry-run` |
| `tests/meta_ads/scripts/test_adsets_update.py` | asserts budget-change `--yes` gate + `--dry-run` |
| `tests/meta_ads/scripts/test_adsets_pause.py` | asserts `status=PAUSED` body + `--dry-run` |
| `tests/meta_ads/scripts/test_ads_create.py` | asserts `PAUSED` default + no-`ACTIVE` path + `--dry-run` |
| `tests/meta_ads/scripts/test_ads_activate.py` | asserts `--yes` gate + `status=ACTIVE` + `--dry-run` |
| `tests/meta_ads/scripts/test_ads_delete.py` | asserts `--yes` gate + DELETE + `--dry-run` |
| `tests/meta_ads/scripts/test_ads_update.py` | asserts name/creative body + `--dry-run` |
| `tests/meta_ads/scripts/test_ads_pause.py` | asserts `status=PAUSED` body + `--dry-run` |
| `tests/meta_ads/scripts/test_creatives_create.py` | asserts story-spec body + `--dry-run` |
| `skills/meta-ads-structure/SKILL.md` | extend (M1 created the read sections) with the CRUD sections + safe-default/gating posture (modify) |
| `CHANGELOG.md` | M2 entry (modify) |

---

## Task 1: `campaigns/create.py` (reference safe-default create)

This is the reference for every `create` in the domain: build the Graph form body, **hard-code `status=PAUSED`** (no flag overrides it), `--dry-run` prints the node/edge + form and returns 0, else `POST` + `check_error` + flatten. The tests pin the safe-default invariant.

**Files:**
- Create: `meta_ads/scripts/campaigns/create.py`
- Create: `tests/meta_ads/scripts/test_campaigns_create.py`

- [ ] **Step 1: Write failing test.** Write `tests/meta_ads/scripts/test_campaigns_create.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.campaigns import create as createcmd
from meta_ads.utils.client import MetaAPIError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.campaigns.create.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.campaigns.create.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def _argv(*extra):
    return [
        "create.py",
        "--account-id",
        "123",
        "--name",
        "Spring Sale",
        "--objective",
        "OUTCOME_SALES",
        *extra,
    ]


def test_create_dry_run_forces_paused_and_skips_post(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(sys, "argv", _argv("--dry-run", "--output", "json")):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["path"] == "act_123/campaigns"
    assert parsed["data"]["status"] == "PAUSED"
    assert parsed["data"]["name"] == "Spring Sale"
    assert parsed["data"]["objective"] == "OUTCOME_SALES"


def test_create_posts_paused_body(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "c9"}
        with patch.object(sys, "argv", _argv()):
            assert createcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "act_123/campaigns"
        data = kwargs.get("data") or args[1]
        assert data["status"] == "PAUSED"
        assert data["name"] == "Spring Sale"
        assert data["objective"] == "OUTCOME_SALES"


def test_create_has_no_active_path(monkeypatch):
    """No flag may produce status=ACTIVE on create (safe-default guardrail)."""
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "c9"}
        # there is no --status/--active flag; argparse rejects an attempt to set one
        with (
            patch.object(sys, "argv", _argv("--status", "ACTIVE")),
            pytest.raises(SystemExit),
        ):
            createcmd.main()
        # and a clean create still pins PAUSED
        with patch.object(sys, "argv", _argv()):
            assert createcmd.main() == 0
        _, kwargs = client.post.call_args
        assert kwargs["data"]["status"] == "PAUSED"
        assert kwargs["data"]["status"] != "ACTIVE"


def test_create_serializes_special_ad_categories(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "c9"}
        with patch.object(sys, "argv", _argv("--special-ad-categories", "HOUSING")):
            assert createcmd.main() == 0
        _, kwargs = client.post.call_args
        assert kwargs["data"]["special_ad_categories"] == '["HOUSING"]'


def test_create_defaults_special_ad_categories_to_none_list(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "c9"}
        with patch.object(sys, "argv", _argv()):
            assert createcmd.main() == 0
        _, kwargs = client.post.call_args
        assert kwargs["data"]["special_ad_categories"] == "[]"


def test_create_surfaces_api_error(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {
            "error": {"message": "bad objective", "code": 100, "fbtrace_id": "Z"}
        }
        with (
            patch.object(sys, "argv", _argv()),
            pytest.raises(MetaAPIError),
        ):
            createcmd.main()
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_campaigns_create.py -v
```
Expected: `ModuleNotFoundError: No module named 'meta_ads.scripts.campaigns.create'`.

- [ ] **Step 3: Implement `meta_ads/scripts/campaigns/create.py`.** Complete code:

```python
"""Create a campaign under an ad account — always PAUSED.

POST /act_<id>/campaigns. The created campaign's ``status`` is hard-coded to
``PAUSED``; there is no flag that yields ``ACTIVE`` (a deliberate guardrail
against accidental spend — activate with campaigns/activate.py, which is
--yes-gated). --dry-run prints the Graph node/edge + form body and skips the POST.
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
    data: dict[str, object] = {
        "name": args.name,
        "objective": args.objective,
        # Safe-default guardrail: never ACTIVE on create.
        "status": "PAUSED",
        "special_ad_categories": json.dumps(args.special_ad_categories or []),
    }
    if args.buying_type:
        data["buying_type"] = args.buying_type
    if args.daily_budget is not None:
        data["daily_budget"] = args.daily_budget
    if args.lifetime_budget is not None:
        data["lifetime_budget"] = args.lifetime_budget
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a PAUSED campaign.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument("--name", required=True, help="Campaign name")
    parser.add_argument(
        "--objective",
        required=True,
        help="Campaign objective (e.g. OUTCOME_SALES, OUTCOME_TRAFFIC)",
    )
    parser.add_argument(
        "--buying_type",
        dest="buying_type",
        help="Buying type (e.g. AUCTION)",
    )
    parser.add_argument(
        "--daily-budget",
        dest="daily_budget",
        type=int,
        help="Daily budget in account minor units (e.g. cents)",
    )
    parser.add_argument(
        "--lifetime-budget",
        dest="lifetime_budget",
        type=int,
        help="Lifetime budget in account minor units (e.g. cents)",
    )
    parser.add_argument(
        "--special-ad-categories",
        dest="special_ad_categories",
        action="append",
        help="Special ad category (repeatable; e.g. HOUSING, EMPLOYMENT, CREDIT)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    path = f"{account_path(args.account_id)}/campaigns"
    data = _build_data(args)

    if args.dry_run:
        print(format_output({"path": path, "data": data}, args.output))
        return 0

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
uv run pytest tests/meta_ads/scripts/test_campaigns_create.py -v
uv run ruff check meta_ads/scripts/campaigns/create.py tests/meta_ads/scripts/test_campaigns_create.py
uv run ruff format meta_ads/scripts/campaigns/create.py tests/meta_ads/scripts/test_campaigns_create.py
git add meta_ads/scripts/campaigns/create.py tests/meta_ads/scripts/test_campaigns_create.py
git commit -m "feat(meta-ads): campaigns/create.py forces status=PAUSED (safe-default)"
```

---

## Task 2: `campaigns/pause.py` (reference status flip)

`POST /<campaign_id>` with `status=PAUSED`. The reference for every `pause.py`: a low-risk status flip, **not** `--yes`-gated, `--dry-run` on every call.

**Files:**
- Create: `meta_ads/scripts/campaigns/pause.py`
- Create: `tests/meta_ads/scripts/test_campaigns_pause.py`

- [ ] **Step 1: Write failing test.** Write `tests/meta_ads/scripts/test_campaigns_pause.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from meta_ads.scripts.campaigns import pause as pausecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.campaigns.pause.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.campaigns.pause.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_pause_dry_run_skips_post(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["pause.py", "--id", "c1", "--dry-run", "--output", "json"]
        ):
            assert pausecmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["path"] == "c1"
    assert parsed["data"]["status"] == "PAUSED"


def test_pause_posts_paused_status(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"success": True}
        with patch.object(sys, "argv", ["pause.py", "--id", "c1"]):
            assert pausecmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "c1"
        assert (kwargs.get("data") or args[1])["status"] == "PAUSED"


def test_pause_not_yes_gated(monkeypatch):
    """Pausing is low-risk: it must run without --yes."""
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"success": True}
        with patch.object(sys, "argv", ["pause.py", "--id", "c1"]):
            assert pausecmd.main() == 0
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_campaigns_pause.py -v
```

- [ ] **Step 3: Implement `meta_ads/scripts/campaigns/pause.py`.** Complete code:

```python
"""Pause a campaign — POST /<campaign_id> with status=PAUSED.

Low-risk status flip; not --yes-gated. --dry-run prints the node + form and
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
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, check_error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pause a campaign.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Campaign id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    path = args.id
    data = {"status": "PAUSED"}

    if args.dry_run:
        print(format_output({"path": path, "data": data}, args.output))
        return 0

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
uv run pytest tests/meta_ads/scripts/test_campaigns_pause.py -v
uv run ruff check meta_ads/scripts/campaigns/pause.py tests/meta_ads/scripts/test_campaigns_pause.py
uv run ruff format meta_ads/scripts/campaigns/pause.py tests/meta_ads/scripts/test_campaigns_pause.py
git add meta_ads/scripts/campaigns/pause.py tests/meta_ads/scripts/test_campaigns_pause.py
git commit -m "feat(meta-ads): campaigns/pause.py (status=PAUSED, no --yes)"
```

---

## Task 3: `campaigns/activate.py` (reference `--yes`-gated status flip)

`POST /<campaign_id>` with `status=ACTIVE`. The only script that sends `ACTIVE`. The reference for every `activate.py`: `--yes`-gated — without `--yes` (and not `--dry-run`) it calls `parser.error(...)` **before any network call**.

**Files:**
- Create: `meta_ads/scripts/campaigns/activate.py`
- Create: `tests/meta_ads/scripts/test_campaigns_activate.py`

- [ ] **Step 1: Write failing test.** Write `tests/meta_ads/scripts/test_campaigns_activate.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.campaigns import activate as activatecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.campaigns.activate.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.campaigns.activate.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_activate_requires_yes(monkeypatch):
    """Without --yes (and not --dry-run) it errors before any network call."""
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        mock_cfg, _, client = _setup_mocks(stack)
        with (
            patch.object(sys, "argv", ["activate.py", "--id", "c1"]),
            pytest.raises(SystemExit),
        ):
            activatecmd.main()
        mock_cfg.assert_not_called()
        assert client.post.call_count == 0


def test_activate_dry_run_skips_post_without_yes(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["activate.py", "--id", "c1", "--dry-run", "--output", "json"]
        ):
            assert activatecmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["path"] == "c1"
    assert parsed["data"]["status"] == "ACTIVE"


def test_activate_with_yes_posts_active(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"success": True}
        with patch.object(sys, "argv", ["activate.py", "--id", "c1", "--yes"]):
            assert activatecmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "c1"
        assert (kwargs.get("data") or args[1])["status"] == "ACTIVE"
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_campaigns_activate.py -v
```

- [ ] **Step 3: Implement `meta_ads/scripts/campaigns/activate.py`.** Complete code:

```python
"""Activate a campaign — POST /<campaign_id> with status=ACTIVE.

The only script that ever sends status=ACTIVE. --yes-gated: without --yes (and
not --dry-run) it errors before any network call. --dry-run prints the node +
form and skips the POST (allowed without --yes, since it touches nothing).
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
    parser = argparse.ArgumentParser(description="Activate a campaign (--yes required).")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Campaign id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    path = args.id
    data = {"status": "ACTIVE"}

    if args.dry_run:
        print(format_output({"path": path, "data": data}, args.output))
        return 0

    if not args.yes:
        parser.error("activating a campaign spends money; pass --yes to confirm")

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
uv run pytest tests/meta_ads/scripts/test_campaigns_activate.py -v
uv run ruff check meta_ads/scripts/campaigns/activate.py tests/meta_ads/scripts/test_campaigns_activate.py
uv run ruff format meta_ads/scripts/campaigns/activate.py tests/meta_ads/scripts/test_campaigns_activate.py
git add meta_ads/scripts/campaigns/activate.py tests/meta_ads/scripts/test_campaigns_activate.py
git commit -m "feat(meta-ads): campaigns/activate.py (status=ACTIVE, --yes-gated)"
```

---

## Task 4: `campaigns/delete.py` (reference `--yes`-gated destructive op)

`DELETE /<campaign_id>`. The reference for every `delete.py`: `--yes`-gated (errors before any network call without it), `--dry-run` prints the intent.

**Files:**
- Create: `meta_ads/scripts/campaigns/delete.py`
- Create: `tests/meta_ads/scripts/test_campaigns_delete.py`

- [ ] **Step 1: Write failing test.** Write `tests/meta_ads/scripts/test_campaigns_delete.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.campaigns import delete as deletecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.campaigns.delete.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.campaigns.delete.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_delete_requires_yes(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        mock_cfg, _, client = _setup_mocks(stack)
        with (
            patch.object(sys, "argv", ["delete.py", "--id", "c1"]),
            pytest.raises(SystemExit),
        ):
            deletecmd.main()
        mock_cfg.assert_not_called()
        assert client.delete.call_count == 0


def test_delete_dry_run_skips_call_without_yes(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["delete.py", "--id", "c1", "--dry-run", "--output", "json"]
        ):
            assert deletecmd.main() == 0
        assert client.delete.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["path"] == "c1"
    assert parsed["method"] == "DELETE"


def test_delete_with_yes_calls_delete(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.delete.return_value = {"success": True}
        with patch.object(sys, "argv", ["delete.py", "--id", "c1", "--yes"]):
            assert deletecmd.main() == 0
        args, _ = client.delete.call_args
        assert args[0] == "c1"
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_campaigns_delete.py -v
```

- [ ] **Step 3: Implement `meta_ads/scripts/campaigns/delete.py`.** Complete code:

```python
"""Delete a campaign — DELETE /<campaign_id>.

Destructive and --yes-gated: without --yes (and not --dry-run) it errors before
any network call. --dry-run prints the intent and skips the call.
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
    parser = argparse.ArgumentParser(description="Delete a campaign (--yes required).")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Campaign id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    path = args.id

    if args.dry_run:
        print(format_output({"path": path, "method": "DELETE"}, args.output))
        return 0

    if not args.yes:
        parser.error("deleting a campaign is irreversible; pass --yes to confirm")

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.delete(path)

    check_error(result)
    print(format_output(result, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/meta_ads/scripts/test_campaigns_delete.py -v
uv run ruff check meta_ads/scripts/campaigns/delete.py tests/meta_ads/scripts/test_campaigns_delete.py
uv run ruff format meta_ads/scripts/campaigns/delete.py tests/meta_ads/scripts/test_campaigns_delete.py
git add meta_ads/scripts/campaigns/delete.py tests/meta_ads/scripts/test_campaigns_delete.py
git commit -m "feat(meta-ads): campaigns/delete.py (DELETE, --yes-gated)"
```

---

## Task 5: `campaigns/update.py` (reference budget-gated update)

`POST /<campaign_id>` for name/budget. The reference for every `update.py`: only the fields given are sent; a **budget change** (`--daily-budget`/`--lifetime-budget`) is `--yes`-gated (errors before the network call without `--yes` and not `--dry-run`); a name-only update is not gated. `--dry-run` prints the body.

**Files:**
- Create: `meta_ads/scripts/campaigns/update.py`
- Create: `tests/meta_ads/scripts/test_campaigns_update.py`

- [ ] **Step 1: Write failing test.** Write `tests/meta_ads/scripts/test_campaigns_update.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.campaigns import update as updatecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.campaigns.update.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.campaigns.update.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_update_name_only_not_gated(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"success": True}
        with patch.object(sys, "argv", ["update.py", "--id", "c1", "--name", "Renamed"]):
            assert updatecmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "c1"
        data = kwargs.get("data") or args[1]
        assert data == {"name": "Renamed"}


def test_update_budget_requires_yes(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        mock_cfg, _, client = _setup_mocks(stack)
        with (
            patch.object(
                sys, "argv", ["update.py", "--id", "c1", "--daily-budget", "5000"]
            ),
            pytest.raises(SystemExit),
        ):
            updatecmd.main()
        mock_cfg.assert_not_called()
        assert client.post.call_count == 0


def test_update_budget_with_yes_posts(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"success": True}
        with patch.object(
            sys, "argv", ["update.py", "--id", "c1", "--daily-budget", "5000", "--yes"]
        ):
            assert updatecmd.main() == 0
        _, kwargs = client.post.call_args
        assert kwargs["data"]["daily_budget"] == 5000


def test_update_budget_dry_run_skips_post_without_yes(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["update.py", "--id", "c1", "--daily-budget", "5000", "--dry-run", "--output", "json"],
        ):
            assert updatecmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["daily_budget"] == 5000


def test_update_requires_a_field(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with (
            patch.object(sys, "argv", ["update.py", "--id", "c1"]),
            pytest.raises(SystemExit),
        ):
            updatecmd.main()
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_campaigns_update.py -v
```

- [ ] **Step 3: Implement `meta_ads/scripts/campaigns/update.py`.** Complete code:

```python
"""Update a campaign — POST /<campaign_id>.

Sends only the fields given. A budget change (--daily-budget/--lifetime-budget)
is --yes-gated (errors before the network call without --yes and not --dry-run);
a name-only update is not gated. --dry-run prints the body and skips the POST.
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


def _build_data(args: argparse.Namespace) -> dict:
    data: dict[str, object] = {}
    if args.name is not None:
        data["name"] = args.name
    if args.status is not None:
        data["status"] = args.status
    if args.daily_budget is not None:
        data["daily_budget"] = args.daily_budget
    if args.lifetime_budget is not None:
        data["lifetime_budget"] = args.lifetime_budget
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update a campaign.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Campaign id")
    parser.add_argument("--name", help="New campaign name")
    parser.add_argument(
        "--status",
        choices=("PAUSED", "ARCHIVED"),
        help="New status (use pause.py/activate.py for PAUSED/ACTIVE flips)",
    )
    parser.add_argument(
        "--daily-budget", dest="daily_budget", type=int, help="Daily budget (minor units)"
    )
    parser.add_argument(
        "--lifetime-budget",
        dest="lifetime_budget",
        type=int,
        help="Lifetime budget (minor units)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    data = _build_data(args)
    if not data:
        parser.error("nothing to update; pass --name/--status/--daily-budget/--lifetime-budget")

    changes_budget = (
        args.daily_budget is not None or args.lifetime_budget is not None
    )

    if args.dry_run:
        print(format_output({"path": args.id, "data": data}, args.output))
        return 0

    if changes_budget and not args.yes:
        parser.error("changing a campaign budget affects spend; pass --yes to confirm")

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.post(args.id, data=data)

    check_error(result)
    print(format_output(result, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/meta_ads/scripts/test_campaigns_update.py -v
uv run ruff check meta_ads/scripts/campaigns/update.py tests/meta_ads/scripts/test_campaigns_update.py
uv run ruff format meta_ads/scripts/campaigns/update.py tests/meta_ads/scripts/test_campaigns_update.py
git add meta_ads/scripts/campaigns/update.py tests/meta_ads/scripts/test_campaigns_update.py
git commit -m "feat(meta-ads): campaigns/update.py (budget change --yes-gated)"
```

---

## Task 6: `adsets/create.py` — mirror the campaign create (safe-default)

Mirrors `campaigns/create.py`: `POST /act_<id>/adsets`, **forces `status=PAUSED`**, no `ACTIVE` path. Ad sets carry the campaign ref, budget, billing/optimization, and a targeting spec (passed as a raw JSON string, the Graph form convention).

**Files:**
- Create: `meta_ads/scripts/adsets/create.py`
- Create: `tests/meta_ads/scripts/test_adsets_create.py`

- [ ] **Step 1: Write failing test.** Write `tests/meta_ads/scripts/test_adsets_create.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.adsets import create as createcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.adsets.create.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.adsets.create.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def _argv(*extra):
    return [
        "create.py",
        "--account-id",
        "123",
        "--name",
        "Broad EU",
        "--campaign-id",
        "c1",
        "--daily-budget",
        "3000",
        "--billing-event",
        "IMPRESSIONS",
        "--optimization-goal",
        "LINK_CLICKS",
        "--targeting",
        '{"geo_locations": {"countries": ["SE"]}}',
        *extra,
    ]


def test_adset_create_dry_run_forces_paused(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(sys, "argv", _argv("--dry-run", "--output", "json")):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["path"] == "act_123/adsets"
    assert parsed["data"]["status"] == "PAUSED"
    assert parsed["data"]["campaign_id"] == "c1"
    assert parsed["data"]["targeting"] == '{"geo_locations": {"countries": ["SE"]}}'


def test_adset_create_posts_paused_body(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "as9"}
        with patch.object(sys, "argv", _argv()):
            assert createcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "act_123/adsets"
        data = kwargs.get("data") or args[1]
        assert data["status"] == "PAUSED"
        assert data["daily_budget"] == 3000
        assert data["billing_event"] == "IMPRESSIONS"
        assert data["optimization_goal"] == "LINK_CLICKS"


def test_adset_create_has_no_active_path(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "as9"}
        with (
            patch.object(sys, "argv", _argv("--status", "ACTIVE")),
            pytest.raises(SystemExit),
        ):
            createcmd.main()
        with patch.object(sys, "argv", _argv()):
            assert createcmd.main() == 0
        _, kwargs = client.post.call_args
        assert kwargs["data"]["status"] == "PAUSED"


def test_adset_create_rejects_bad_targeting_json(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _setup_mocks(stack)
        argv = [
            "create.py",
            "--account-id",
            "123",
            "--name",
            "X",
            "--campaign-id",
            "c1",
            "--daily-budget",
            "3000",
            "--billing-event",
            "IMPRESSIONS",
            "--optimization-goal",
            "LINK_CLICKS",
            "--targeting",
            "{not json",
        ]
        with (
            patch.object(sys, "argv", argv),
            pytest.raises(SystemExit),
        ):
            createcmd.main()
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_adsets_create.py -v
```

- [ ] **Step 3: Implement `meta_ads/scripts/adsets/create.py`.** Complete code:

```python
"""Create an ad set under an ad account — always PAUSED.

POST /act_<id>/adsets. Forces status=PAUSED (no ACTIVE path; activate with
adsets/activate.py, --yes-gated). The targeting spec is a raw JSON string (the
Graph form convention); it is validated as JSON but forwarded unchanged.
--dry-run prints the node/edge + form body and skips the POST.
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
    data: dict[str, object] = {
        "name": args.name,
        "campaign_id": args.campaign_id,
        "billing_event": args.billing_event,
        "optimization_goal": args.optimization_goal,
        "targeting": args.targeting,
        # Safe-default guardrail: never ACTIVE on create.
        "status": "PAUSED",
    }
    if args.daily_budget is not None:
        data["daily_budget"] = args.daily_budget
    if args.lifetime_budget is not None:
        data["lifetime_budget"] = args.lifetime_budget
    if args.bid_amount is not None:
        data["bid_amount"] = args.bid_amount
    if args.start_time:
        data["start_time"] = args.start_time
    if args.end_time:
        data["end_time"] = args.end_time
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a PAUSED ad set.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument("--name", required=True, help="Ad set name")
    parser.add_argument("--campaign-id", dest="campaign_id", required=True)
    parser.add_argument(
        "--billing-event", dest="billing_event", required=True, help="e.g. IMPRESSIONS"
    )
    parser.add_argument(
        "--optimization-goal",
        dest="optimization_goal",
        required=True,
        help="e.g. LINK_CLICKS, OFFSITE_CONVERSIONS",
    )
    parser.add_argument(
        "--targeting", required=True, help="Targeting spec as a JSON string"
    )
    parser.add_argument(
        "--daily-budget", dest="daily_budget", type=int, help="Daily budget (minor units)"
    )
    parser.add_argument(
        "--lifetime-budget",
        dest="lifetime_budget",
        type=int,
        help="Lifetime budget (minor units)",
    )
    parser.add_argument(
        "--bid-amount", dest="bid_amount", type=int, help="Bid amount (minor units)"
    )
    parser.add_argument("--start-time", dest="start_time", help="ISO 8601 start time")
    parser.add_argument("--end-time", dest="end_time", help="ISO 8601 end time")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    if args.daily_budget is None and args.lifetime_budget is None:
        parser.error("one of --daily-budget or --lifetime-budget is required")
    try:
        json.loads(args.targeting)
    except json.JSONDecodeError as exc:
        parser.error(f"--targeting is not valid JSON: {exc}")

    path = f"{account_path(args.account_id)}/adsets"
    data = _build_data(args)

    if args.dry_run:
        print(format_output({"path": path, "data": data}, args.output))
        return 0

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
uv run pytest tests/meta_ads/scripts/test_adsets_create.py -v
uv run ruff check meta_ads/scripts/adsets/create.py tests/meta_ads/scripts/test_adsets_create.py
uv run ruff format meta_ads/scripts/adsets/create.py tests/meta_ads/scripts/test_adsets_create.py
git add meta_ads/scripts/adsets/create.py tests/meta_ads/scripts/test_adsets_create.py
git commit -m "feat(meta-ads): adsets/create.py forces status=PAUSED (safe-default)"
```

---

## Task 7: `adsets/{pause,activate,delete,update}.py` — mirror the campaign set

Mirror Tasks 2–5 for ad sets. The bodies are identical except the node is an ad set id and the help/error text says "ad set". Write all four scripts and their tests in one task.

**Files:**
- Create: `meta_ads/scripts/adsets/pause.py`
- Create: `meta_ads/scripts/adsets/activate.py`
- Create: `meta_ads/scripts/adsets/delete.py`
- Create: `meta_ads/scripts/adsets/update.py`
- Create: `tests/meta_ads/scripts/test_adsets_pause.py`
- Create: `tests/meta_ads/scripts/test_adsets_activate.py`
- Create: `tests/meta_ads/scripts/test_adsets_delete.py`
- Create: `tests/meta_ads/scripts/test_adsets_update.py`

- [ ] **Step 1: Write the four failing tests.** Copy `tests/meta_ads/scripts/test_campaigns_{pause,activate,delete,update}.py` to the `test_adsets_*` names, then in each replace `campaigns` with `adsets` in the import + patch targets (`meta_ads.scripts.adsets.<op>`) and rename the entrypoint script tokens (`pause.py`→still `pause.py` in argv; the module alias stays `pausecmd`/`activatecmd`/`deletecmd`/`updatecmd`). Keep the same assertions: `pause` posts `status=PAUSED` and is not `--yes`-gated; `activate` requires `--yes`, dry-run prints `status=ACTIVE`; `delete` requires `--yes`, dry-run prints `method=DELETE`; `update` gates budget changes behind `--yes` and rejects an empty update.

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_adsets_pause.py tests/meta_ads/scripts/test_adsets_activate.py tests/meta_ads/scripts/test_adsets_delete.py tests/meta_ads/scripts/test_adsets_update.py -v
```
Expected: `ModuleNotFoundError` for the four `meta_ads.scripts.adsets.*` modules.

- [ ] **Step 3: Implement the four ad set scripts.** Each is the campaign counterpart from Tasks 2–5 with "campaign" → "ad set" in docstring/help/error text. `meta_ads/scripts/adsets/pause.py`:

```python
"""Pause an ad set — POST /<adset_id> with status=PAUSED.

Low-risk status flip; not --yes-gated. --dry-run prints the node + form and
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
from meta_ads.utils.cli import (
    add_common_flags,
    add_meta_flags,
    configure_logging_from_args,
    format_output,
)
from meta_ads.utils.client import MetaClient, check_error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pause an ad set.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Ad set id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    path = args.id
    data = {"status": "PAUSED"}

    if args.dry_run:
        print(format_output({"path": path, "data": data}, args.output))
        return 0

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.post(path, data=data)

    check_error(result)
    print(format_output(result, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`meta_ads/scripts/adsets/activate.py`:

```python
"""Activate an ad set — POST /<adset_id> with status=ACTIVE.

--yes-gated: without --yes (and not --dry-run) it errors before any network
call. --dry-run prints the node + form and skips the POST.
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
    parser = argparse.ArgumentParser(description="Activate an ad set (--yes required).")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Ad set id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    path = args.id
    data = {"status": "ACTIVE"}

    if args.dry_run:
        print(format_output({"path": path, "data": data}, args.output))
        return 0

    if not args.yes:
        parser.error("activating an ad set spends money; pass --yes to confirm")

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.post(path, data=data)

    check_error(result)
    print(format_output(result, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`meta_ads/scripts/adsets/delete.py`:

```python
"""Delete an ad set — DELETE /<adset_id>.

Destructive and --yes-gated: without --yes (and not --dry-run) it errors before
any network call. --dry-run prints the intent and skips the call.
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
    parser = argparse.ArgumentParser(description="Delete an ad set (--yes required).")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Ad set id")
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    path = args.id

    if args.dry_run:
        print(format_output({"path": path, "method": "DELETE"}, args.output))
        return 0

    if not args.yes:
        parser.error("deleting an ad set is irreversible; pass --yes to confirm")

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.delete(path)

    check_error(result)
    print(format_output(result, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`meta_ads/scripts/adsets/update.py`:

```python
"""Update an ad set — POST /<adset_id>.

Sends only the fields given. A budget change (--daily-budget/--lifetime-budget)
is --yes-gated (errors before the network call without --yes and not --dry-run);
a name-only update is not gated. --dry-run prints the body and skips the POST.
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


def _build_data(args: argparse.Namespace) -> dict:
    data: dict[str, object] = {}
    if args.name is not None:
        data["name"] = args.name
    if args.status is not None:
        data["status"] = args.status
    if args.daily_budget is not None:
        data["daily_budget"] = args.daily_budget
    if args.lifetime_budget is not None:
        data["lifetime_budget"] = args.lifetime_budget
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update an ad set.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Ad set id")
    parser.add_argument("--name", help="New ad set name")
    parser.add_argument(
        "--status",
        choices=("PAUSED", "ARCHIVED"),
        help="New status (use pause.py/activate.py for PAUSED/ACTIVE flips)",
    )
    parser.add_argument(
        "--daily-budget", dest="daily_budget", type=int, help="Daily budget (minor units)"
    )
    parser.add_argument(
        "--lifetime-budget",
        dest="lifetime_budget",
        type=int,
        help="Lifetime budget (minor units)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    data = _build_data(args)
    if not data:
        parser.error("nothing to update; pass --name/--status/--daily-budget/--lifetime-budget")

    changes_budget = args.daily_budget is not None or args.lifetime_budget is not None

    if args.dry_run:
        print(format_output({"path": args.id, "data": data}, args.output))
        return 0

    if changes_budget and not args.yes:
        parser.error("changing an ad set budget affects spend; pass --yes to confirm")

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.post(args.id, data=data)

    check_error(result)
    print(format_output(result, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/meta_ads/scripts/test_adsets_pause.py tests/meta_ads/scripts/test_adsets_activate.py tests/meta_ads/scripts/test_adsets_delete.py tests/meta_ads/scripts/test_adsets_update.py -v
uv run ruff check meta_ads/scripts/adsets/ tests/meta_ads/scripts/test_adsets_pause.py tests/meta_ads/scripts/test_adsets_activate.py tests/meta_ads/scripts/test_adsets_delete.py tests/meta_ads/scripts/test_adsets_update.py
uv run ruff format meta_ads/scripts/adsets/ tests/meta_ads/scripts/test_adsets_pause.py tests/meta_ads/scripts/test_adsets_activate.py tests/meta_ads/scripts/test_adsets_delete.py tests/meta_ads/scripts/test_adsets_update.py
git add meta_ads/scripts/adsets/pause.py meta_ads/scripts/adsets/activate.py meta_ads/scripts/adsets/delete.py meta_ads/scripts/adsets/update.py tests/meta_ads/scripts/test_adsets_pause.py tests/meta_ads/scripts/test_adsets_activate.py tests/meta_ads/scripts/test_adsets_delete.py tests/meta_ads/scripts/test_adsets_update.py
git commit -m "feat(meta-ads): adsets/{pause,activate,delete,update}.py (gated like campaigns)"
```

---

## Task 8: `ads/create.py` — mirror the safe-default create (references a creative)

`POST /act_<id>/ads`, **forces `status=PAUSED`**, no `ACTIVE` path. An ad ties an ad set to a creative: `--adset-id` plus a creative reference (`--creative-id`, sent as the `creative` form param `{"creative_id": ...}` JSON).

**Files:**
- Create: `meta_ads/scripts/ads/create.py`
- Create: `tests/meta_ads/scripts/test_ads_create.py`

- [ ] **Step 1: Write failing test.** Write `tests/meta_ads/scripts/test_ads_create.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.ads import create as createcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.ads.create.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.ads.create.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def _argv(*extra):
    return [
        "create.py",
        "--account-id",
        "123",
        "--name",
        "Ad 1",
        "--adset-id",
        "as1",
        "--creative-id",
        "cr1",
        *extra,
    ]


def test_ad_create_dry_run_forces_paused(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(sys, "argv", _argv("--dry-run", "--output", "json")):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["path"] == "act_123/ads"
    assert parsed["data"]["status"] == "PAUSED"
    assert parsed["data"]["adset_id"] == "as1"
    assert parsed["data"]["creative"] == '{"creative_id": "cr1"}'


def test_ad_create_posts_paused_body(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "ad9"}
        with patch.object(sys, "argv", _argv()):
            assert createcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "act_123/ads"
        data = kwargs.get("data") or args[1]
        assert data["status"] == "PAUSED"
        assert data["creative"] == '{"creative_id": "cr1"}'


def test_ad_create_has_no_active_path(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "ad9"}
        with (
            patch.object(sys, "argv", _argv("--status", "ACTIVE")),
            pytest.raises(SystemExit),
        ):
            createcmd.main()
        with patch.object(sys, "argv", _argv()):
            assert createcmd.main() == 0
        _, kwargs = client.post.call_args
        assert kwargs["data"]["status"] == "PAUSED"
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_ads_create.py -v
```

- [ ] **Step 3: Implement `meta_ads/scripts/ads/create.py`.** Complete code:

```python
"""Create an ad under an ad account — always PAUSED.

POST /act_<id>/ads. Forces status=PAUSED (no ACTIVE path; activate with
ads/activate.py, --yes-gated). An ad ties an ad set to a creative: --adset-id
plus --creative-id (sent as the Graph ``creative`` form param,
{"creative_id": ...} JSON). --dry-run prints the node/edge + form and skips POST.
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a PAUSED ad.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument("--name", required=True, help="Ad name")
    parser.add_argument("--adset-id", dest="adset_id", required=True)
    parser.add_argument(
        "--creative-id", dest="creative_id", required=True, help="Existing ad creative id"
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    path = f"{account_path(args.account_id)}/ads"
    data = {
        "name": args.name,
        "adset_id": args.adset_id,
        "creative": json.dumps({"creative_id": args.creative_id}),
        # Safe-default guardrail: never ACTIVE on create.
        "status": "PAUSED",
    }

    if args.dry_run:
        print(format_output({"path": path, "data": data}, args.output))
        return 0

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
uv run pytest tests/meta_ads/scripts/test_ads_create.py -v
uv run ruff check meta_ads/scripts/ads/create.py tests/meta_ads/scripts/test_ads_create.py
uv run ruff format meta_ads/scripts/ads/create.py tests/meta_ads/scripts/test_ads_create.py
git add meta_ads/scripts/ads/create.py tests/meta_ads/scripts/test_ads_create.py
git commit -m "feat(meta-ads): ads/create.py forces status=PAUSED (safe-default)"
```

---

## Task 9: `ads/{pause,activate,delete,update}.py` — mirror the campaign/adset set

Mirror Tasks 2–5 for ads. `ads/update.py` updates `--name` and/or the creative reference (`--creative-id`); there is no ad-level budget, so the only gating is `delete`/`activate`.

**Files:**
- Create: `meta_ads/scripts/ads/pause.py`
- Create: `meta_ads/scripts/ads/activate.py`
- Create: `meta_ads/scripts/ads/delete.py`
- Create: `meta_ads/scripts/ads/update.py`
- Create: `tests/meta_ads/scripts/test_ads_pause.py`
- Create: `tests/meta_ads/scripts/test_ads_activate.py`
- Create: `tests/meta_ads/scripts/test_ads_delete.py`
- Create: `tests/meta_ads/scripts/test_ads_update.py`

- [ ] **Step 1: Write the four failing tests.** For `pause`/`activate`/`delete`, copy the adset counterparts (Task 7) to `test_ads_*`, swapping `adsets`→`ads` in import + patch targets and "ad set"→"ad" expectations. For `test_ads_update.py`, the body differs (name + creative, no budget gate):

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.ads import update as updatecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.ads.update.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.ads.update.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_ad_update_name(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"success": True}
        with patch.object(sys, "argv", ["update.py", "--id", "ad1", "--name", "Renamed"]):
            assert updatecmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "ad1"
        assert (kwargs.get("data") or args[1]) == {"name": "Renamed"}


def test_ad_update_creative_serializes(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"success": True}
        with patch.object(
            sys, "argv", ["update.py", "--id", "ad1", "--creative-id", "cr2"]
        ):
            assert updatecmd.main() == 0
        _, kwargs = client.post.call_args
        assert kwargs["data"]["creative"] == '{"creative_id": "cr2"}'


def test_ad_update_dry_run_skips_post(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["update.py", "--id", "ad1", "--name", "N", "--dry-run", "--output", "json"]
        ):
            assert updatecmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["name"] == "N"


def test_ad_update_requires_a_field(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with (
            patch.object(sys, "argv", ["update.py", "--id", "ad1"]),
            pytest.raises(SystemExit),
        ):
            updatecmd.main()
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_ads_pause.py tests/meta_ads/scripts/test_ads_activate.py tests/meta_ads/scripts/test_ads_delete.py tests/meta_ads/scripts/test_ads_update.py -v
```

- [ ] **Step 3: Implement the four ad scripts.** `pause`/`activate`/`delete` are the adset counterparts (Task 7) with "ad set"→"ad" and `--id` help "Ad id". `meta_ads/scripts/ads/update.py`:

```python
"""Update an ad — POST /<ad_id>.

Sends only the fields given: --name and/or a creative swap (--creative-id, sent
as the Graph ``creative`` form param). No ad-level budget, so no budget gate.
--dry-run prints the body and skips the POST.
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
from meta_ads.utils.client import MetaClient, check_error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update an ad.")
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--id", required=True, help="Ad id")
    parser.add_argument("--name", help="New ad name")
    parser.add_argument(
        "--creative-id", dest="creative_id", help="Swap to this existing creative id"
    )
    parser.add_argument(
        "--status",
        choices=("PAUSED", "ARCHIVED"),
        help="New status (use pause.py/activate.py for PAUSED/ACTIVE flips)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    data: dict[str, object] = {}
    if args.name is not None:
        data["name"] = args.name
    if args.status is not None:
        data["status"] = args.status
    if args.creative_id is not None:
        data["creative"] = json.dumps({"creative_id": args.creative_id})
    if not data:
        parser.error("nothing to update; pass --name/--creative-id/--status")

    if args.dry_run:
        print(format_output({"path": args.id, "data": data}, args.output))
        return 0

    cfg = load_config(args.config)
    with MetaClient(config=cfg, api_version=args.api_version) as client:
        result = client.post(args.id, data=data)

    check_error(result)
    print(format_output(result, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

For reference, `meta_ads/scripts/ads/pause.py`, `ads/activate.py`, and `ads/delete.py` are byte-for-byte the adset versions from Task 7 with these substitutions: description "ad set"→"ad", `--id` help "Ad set id"→"Ad id", and the `parser.error` text "an ad set"→"an ad".

- [ ] **Step 4: Run, confirm pass + ruff + commit.**

```bash
uv run pytest tests/meta_ads/scripts/test_ads_pause.py tests/meta_ads/scripts/test_ads_activate.py tests/meta_ads/scripts/test_ads_delete.py tests/meta_ads/scripts/test_ads_update.py -v
uv run ruff check meta_ads/scripts/ads/ tests/meta_ads/scripts/test_ads_pause.py tests/meta_ads/scripts/test_ads_activate.py tests/meta_ads/scripts/test_ads_delete.py tests/meta_ads/scripts/test_ads_update.py
uv run ruff format meta_ads/scripts/ads/ tests/meta_ads/scripts/test_ads_pause.py tests/meta_ads/scripts/test_ads_activate.py tests/meta_ads/scripts/test_ads_delete.py tests/meta_ads/scripts/test_ads_update.py
git add meta_ads/scripts/ads/pause.py meta_ads/scripts/ads/activate.py meta_ads/scripts/ads/delete.py meta_ads/scripts/ads/update.py tests/meta_ads/scripts/test_ads_pause.py tests/meta_ads/scripts/test_ads_activate.py tests/meta_ads/scripts/test_ads_delete.py tests/meta_ads/scripts/test_ads_update.py
git commit -m "feat(meta-ads): ads/{pause,activate,delete,update}.py (gated; update swaps creative)"
```

---

## Task 10: `creatives/create.py` — wire an existing asset into a creative

`POST /act_<id>/adcreatives`. Producing assets is out of scope (spec §2); this wires an **existing** asset: `--object-story-spec` (a raw JSON string — the page-post/link spec) or `--image-hash` + `--page-id` for a simple link creative. Not a status-bearing entity, so no `PAUSED`/gating; `--dry-run` applies.

**Files:**
- Create: `meta_ads/scripts/creatives/create.py`
- Create: `tests/meta_ads/scripts/test_creatives_create.py`

- [ ] **Step 1: Write failing test.** Write `tests/meta_ads/scripts/test_creatives_create.py`:

```python
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.creatives import create as createcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.creatives.create.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.creatives.create.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


_SPEC = '{"page_id": "P1", "link_data": {"link": "https://example.com", "image_hash": "H1"}}'


def test_creative_create_dry_run_skips_post(monkeypatch, capsys):
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
                "Link Creative",
                "--object-story-spec",
                _SPEC,
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["path"] == "act_123/adcreatives"
    assert parsed["data"]["name"] == "Link Creative"
    assert parsed["data"]["object_story_spec"] == _SPEC


def test_creative_create_posts_spec(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "cr9"}
        with patch.object(
            sys,
            "argv",
            ["create.py", "--account-id", "123", "--name", "C", "--object-story-spec", _SPEC],
        ):
            assert createcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "act_123/adcreatives"
        assert (kwargs.get("data") or args[1])["object_story_spec"] == _SPEC


def test_creative_create_rejects_bad_spec_json(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with (
            patch.object(
                sys,
                "argv",
                ["create.py", "--account-id", "123", "--name", "C", "--object-story-spec", "{bad"],
            ),
            pytest.raises(SystemExit),
        ):
            createcmd.main()


def test_creative_create_requires_spec(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with (
            patch.object(sys, "argv", ["create.py", "--account-id", "123", "--name", "C"]),
            pytest.raises(SystemExit),
        ):
            createcmd.main()
```

- [ ] **Step 2: Run, confirm fail.**

```bash
uv run pytest tests/meta_ads/scripts/test_creatives_create.py -v
```

- [ ] **Step 3: Implement `meta_ads/scripts/creatives/create.py`.** Complete code:

```python
"""Create an ad creative from an existing asset.

POST /act_<id>/adcreatives. Asset *production* is out of scope (spec §2); this
wires an existing page post / link spec into a creative object via
--object-story-spec (a raw JSON string, validated then forwarded unchanged — the
Graph form convention). Not a status-bearing entity, so no PAUSED/gating.
--dry-run prints the node/edge + form and skips the POST.
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create an ad creative from an existing asset/spec."
    )
    add_common_flags(parser)
    add_meta_flags(parser)
    parser.add_argument("--account-id", dest="account_id", required=True)
    parser.add_argument("--name", required=True, help="Creative name")
    parser.add_argument(
        "--object-story-spec",
        dest="object_story_spec",
        required=True,
        help="Object story spec as a JSON string (page post / link spec)",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    try:
        json.loads(args.object_story_spec)
    except json.JSONDecodeError as exc:
        parser.error(f"--object-story-spec is not valid JSON: {exc}")

    path = f"{account_path(args.account_id)}/adcreatives"
    data = {"name": args.name, "object_story_spec": args.object_story_spec}

    if args.dry_run:
        print(format_output({"path": path, "data": data}, args.output))
        return 0

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
uv run pytest tests/meta_ads/scripts/test_creatives_create.py -v
uv run ruff check meta_ads/scripts/creatives/create.py tests/meta_ads/scripts/test_creatives_create.py
uv run ruff format meta_ads/scripts/creatives/create.py tests/meta_ads/scripts/test_creatives_create.py
git add meta_ads/scripts/creatives/create.py tests/meta_ads/scripts/test_creatives_create.py
git commit -m "feat(meta-ads): creatives/create.py wires an existing object_story_spec"
```

---

## Task 11: Extend the `meta-ads-structure` skill with the CRUD sections

M1 created `skills/meta-ads-structure/SKILL.md` with the read sections. Extend it with the write half, making the safe-default + gating posture explicit.

**Files:**
- Modify: `skills/meta-ads-structure/SKILL.md`

- [ ] **Step 1: Add the CRUD sections.** Append sections documenting `campaigns/{create,update,pause,activate,delete}`, `adsets/{create,update,pause,activate,delete}`, `ads/{create,update,pause,activate,delete}`, and `creatives/create`. Extend the front-matter `description` with the write triggers: "create a Meta campaign", "create an ad set", "create an ad", "pause campaign", "activate campaign", "delete ad set", "change campaign budget", "create an ad creative". The body MUST state the safety posture prominently:
  - **Every `create` makes a PAUSED entity** — there is no flag to create something ACTIVE. This is a deliberate guardrail against accidental ad spend.
  - **`activate.py` is separate and `--yes`-gated** — it is the only script that sets `status=ACTIVE`.
  - **`delete.py` is `--yes`-gated**; a **budget change** on `update.py` (`--daily-budget`/`--lifetime-budget`) is `--yes`-gated.
  - **`--dry-run` on every write** prints the Graph node/edge + form params and exits 0 without calling the API.
  - Budgets are in the account's **minor units** (e.g. cents); targeting and object-story specs are passed as **JSON strings**.
  - Defer Conversions API / catalog management and asset *production* to direct API use.

- [ ] **Step 2: Commit.**

```bash
git add skills/meta-ads-structure/SKILL.md
git commit -m "docs(meta-ads): extend meta-ads-structure skill with CRUD + safe-default posture"
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
Expected: all green; the new `tests/meta_ads/scripts/test_{campaigns,adsets,ads,creatives}_*` tests are collected and pass; M1 reads/insights and existing Shopify/Klaviyo tests unaffected.

- [ ] **Step 2: Smoke each write script's `--help` and a representative `--dry-run`.**

```bash
uv run meta_ads/scripts/campaigns/create.py --help
uv run meta_ads/scripts/campaigns/activate.py --help
uv run meta_ads/scripts/campaigns/delete.py --help
uv run meta_ads/scripts/adsets/create.py --help
uv run meta_ads/scripts/ads/create.py --help
uv run meta_ads/scripts/creatives/create.py --help
META_ACCESS_TOKEN=dummy uv run meta_ads/scripts/campaigns/create.py --account-id 123 --name Smoke --objective OUTCOME_TRAFFIC --dry-run --output json
META_ACCESS_TOKEN=dummy uv run meta_ads/scripts/campaigns/activate.py --id c1 --output json 2>&1 | head -5
```
Expected: help prints for every script; the campaign `--dry-run` prints a body with `"status": "PAUSED"` and makes no network call; `activate.py` without `--yes`/`--dry-run` exits non-zero with the "pass --yes to confirm" message.

- [ ] **Step 3: Verify the safe-default invariant across all creates.**

```bash
uv run pytest tests/meta_ads/scripts/ -k "create and (paused or active)" -v
```
Expected: the `test_*_create.py` PAUSED-default and no-ACTIVE-path tests all pass for campaigns, adsets, and ads.

- [ ] **Step 4: Update `CHANGELOG.md`.** Add an entry under a new version heading (bump the M1 `0.9.0` minor line to `## [0.10.0] — 2026-05-29`) noting: Meta Ads structure CRUD (`campaigns/{create,update,pause,activate,delete}`, `adsets/{create,update,pause,activate,delete}`, `ads/{create,update,pause,activate,delete}`, `creatives/create`). Emphasize the safety posture: every `create` forces `status=PAUSED` (no ACTIVE-on-create path); `activate.py` is separate and `--yes`-gated; `delete.py` and budget changes on `update.py` are `--yes`-gated; `--dry-run` on every write prints the Graph request. Note the `meta-ads-structure` skill now covers the full read+write cluster.

- [ ] **Step 5: Commit.**

```bash
git add CHANGELOG.md
git commit -m "docs(meta-ads): CHANGELOG for Meta Ads structure CRUD (M2)"
```

---

## Definition of Done

(Scoped to M2, per spec §11/§12.)

- [ ] Structure CRUD per spec §5 M2 is present: `campaigns/{create,update,pause,activate,delete}`, `adsets/{create,update,pause,activate,delete}`, `ads/{create,update,pause,activate,delete}`, and `creatives/create`.
- [ ] **Safe-default create:** every `create` script forces `status=PAUSED`; no flag yields `ACTIVE`. Each create's tests assert both that `PAUSED` is in the request body **and** that there is no `ACTIVE` path (campaigns, adsets, ads).
- [ ] **`activate.py` is separate and `--yes`-gated** (the only scripts sending `status=ACTIVE`); without `--yes` (and not `--dry-run`) they call `parser.error(...)` before any network call. Tests prove the gate (config/load and `client.post` not reached).
- [ ] **`delete.py` is `--yes`-gated** (DELETE), and a **budget change** on `campaigns/update.py` / `adsets/update.py` (`--daily-budget`/`--lifetime-budget`) is `--yes`-gated; name-only updates and `pause.py` are not gated. Tests prove each gate.
- [ ] **`--dry-run` on every write** prints the Graph node/edge + form params (or `method=DELETE`) and returns 0 without calling the API; tests assert `client.post`/`client.delete` is not called under `--dry-run`.
- [ ] Writes go through the existing `MetaClient.post(path, data=...)` / `MetaClient.delete(path, ...)`; `check_error` surfaces Graph errors (`MetaAPIError` with `fbtrace_id`) after every live call. No `core/` or `MetaClient` changes.
- [ ] `adsets/create.py` validates `--targeting` as JSON and forwards it unchanged; `creatives/create.py` validates `--object-story-spec` as JSON; `ads/create.py`/`ads/update.py` serialize the creative reference to `{"creative_id": ...}`.
- [ ] Per-script unit tests green, mocking `MetaClient` (no live calls); any integration tests gated by `META_INTEGRATION_TESTS=1` and skipped by default.
- [ ] `meta-ads-structure` skill extended to cover the CRUD sections with the safe-default-`PAUSED` and `--yes`/`--dry-run` posture stated prominently.
- [ ] Full `uv run pytest tests/` green; `ruff check .` and `ruff format --check .` clean. CHANGELOG bumped to `0.10.0`.
