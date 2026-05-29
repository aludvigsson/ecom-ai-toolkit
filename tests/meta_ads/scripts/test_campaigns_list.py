import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from meta_ads.scripts.campaigns import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.campaigns.list.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.campaigns.list.MetaClient"))
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_campaigns_list_normalizes_account_and_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [
                {
                    "id": "c1",
                    "name": "Spring Sale",
                    "objective": "OUTCOME_SALES",
                    "status": "PAUSED",
                    "effective_status": "PAUSED",
                }
            ]
        )
        with patch.object(sys, "argv", ["list.py", "--account-id", "123", "--output", "json"]):
            assert listcmd.main() == 0
        args, _ = client.paginate.call_args
        assert args[0] == "act_123/campaigns"
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "c1"
    assert parsed[0]["objective"] == "OUTCOME_SALES"


def test_campaigns_list_status_filter_builds_param(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py", "--account-id", "123", "--status", "ACTIVE"]):
            assert listcmd.main() == 0
        _, kwargs = client.paginate.call_args
        assert kwargs["params"]["effective_status"] == '["ACTIVE"]'
