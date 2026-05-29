import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from meta_ads.scripts.audiences import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.audiences.list.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.audiences.list.MetaClient"))
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_audiences_list_normalizes_account_and_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [
                {
                    "id": "aud1",
                    "name": "Newsletter buyers",
                    "subtype": "CUSTOM",
                    "approximate_count_lower_bound": 1000,
                    "operation_status": {"code": 200, "description": "Normal"},
                }
            ]
        )
        with patch.object(sys, "argv", ["list.py", "--account-id", "123", "--output", "json"]):
            assert listcmd.main() == 0
        args, kwargs = client.paginate.call_args
        assert args[0] == "act_123/customaudiences"
        params = kwargs.get("params") or args[1]
        assert "name" in params["fields"]
        assert kwargs["limit"] == 50
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "aud1"
    assert parsed[0]["subtype"] == "CUSTOM"


def test_audiences_list_passes_limit(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py", "--account-id", "act_123", "--limit", "5"]):
            assert listcmd.main() == 0
        args, kwargs = client.paginate.call_args
        assert args[0] == "act_123/customaudiences"
        assert kwargs["limit"] == 5
