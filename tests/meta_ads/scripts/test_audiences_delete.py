import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.audiences import delete as delcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.audiences.delete.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.audiences.delete.MetaClient"))
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
