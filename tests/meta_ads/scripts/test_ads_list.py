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
        with patch.object(sys, "argv", ["list.py", "--account-id", "123", "--output", "json"]):
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
