import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from meta_ads.scripts.creatives import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.creatives.list.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.creatives.list.MetaClient"))
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_creatives_list_normalizes_account(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [{"id": "cr1", "name": "Hero", "object_type": "SHARE", "status": "ACTIVE"}]
        )
        with patch.object(sys, "argv", ["list.py", "--account-id", "123", "--output", "json"]):
            assert listcmd.main() == 0
        args, _ = client.paginate.call_args
        assert args[0] == "act_123/adcreatives"
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "cr1"
    assert parsed[0]["object_type"] == "SHARE"
