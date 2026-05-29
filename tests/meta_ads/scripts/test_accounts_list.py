import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from meta_ads.scripts.accounts import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.accounts.list.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.accounts.list.MetaClient"))
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_accounts_list_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [
                {
                    "id": "act_123",
                    "account_id": "123",
                    "name": "Main Ad Account",
                    "account_status": 1,
                    "currency": "USD",
                }
            ]
        )
        with patch.object(sys, "argv", ["list.py", "--business-id", "999", "--output", "json"]):
            assert listcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "act_123"
    assert parsed[0]["name"] == "Main Ad Account"
    assert parsed[0]["currency"] == "USD"


def test_accounts_list_uses_business_node_and_fields(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py", "--business-id", "999"]):
            assert listcmd.main() == 0
        args, kwargs = client.paginate.call_args
        assert args[0] == "999/owned_ad_accounts"
        params = kwargs.get("params") or args[1]
        assert "name" in params["fields"]
        assert kwargs["limit"] == 50


def test_accounts_list_defaults_to_me_node(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    # skip .env.local loading so META_BUSINESS_ID is genuinely absent
    monkeypatch.setattr("core.secrets._env_loaded", True)
    monkeypatch.delenv("META_BUSINESS_ID", raising=False)
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py"]):
            assert listcmd.main() == 0
        args, _ = client.paginate.call_args
        assert args[0] == "me/adaccounts"


def test_accounts_list_uses_business_id_secret(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    monkeypatch.setattr("core.secrets._env_loaded", True)
    monkeypatch.setenv("META_BUSINESS_ID", "555")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py"]):
            assert listcmd.main() == 0
        args, _ = client.paginate.call_args
        assert args[0] == "555/owned_ad_accounts"
