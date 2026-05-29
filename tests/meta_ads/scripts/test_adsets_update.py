import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.adsets import update as updatecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.adsets.update.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.adsets.update.MetaClient"))
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
            patch.object(sys, "argv", ["update.py", "--id", "c1", "--daily-budget", "5000"]),
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
