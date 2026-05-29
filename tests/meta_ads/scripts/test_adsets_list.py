import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.adsets import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.adsets.list.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.adsets.list.MetaClient"))
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_adsets_list_under_account(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [{"id": "as1", "name": "Broad", "status": "PAUSED", "campaign_id": "c1"}]
        )
        with patch.object(sys, "argv", ["list.py", "--account-id", "123", "--output", "json"]):
            assert listcmd.main() == 0
        args, _ = client.paginate.call_args
        assert args[0] == "act_123/adsets"
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "as1"


def test_adsets_list_under_campaign(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py", "--campaign-id", "c1"]):
            assert listcmd.main() == 0
        args, _ = client.paginate.call_args
        assert args[0] == "c1/adsets"


def test_adsets_list_requires_a_parent(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with (
            patch.object(sys, "argv", ["list.py"]),
            pytest.raises(SystemExit),
        ):
            listcmd.main()
