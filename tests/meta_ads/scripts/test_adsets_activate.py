import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.adsets import activate as activatecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.adsets.activate.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.adsets.activate.MetaClient"))
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
