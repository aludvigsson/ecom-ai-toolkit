import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.adsets import delete as deletecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.adsets.delete.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.adsets.delete.MetaClient"))
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
