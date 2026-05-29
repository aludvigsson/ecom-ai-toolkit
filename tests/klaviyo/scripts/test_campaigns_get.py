import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.campaigns import get as getcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.campaigns.get.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.campaigns.get.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_get_campaign_by_id(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "data": {
                "id": "CMP1",
                "type": "campaign",
                "attributes": {"name": "Spring Sale", "status": "Draft"},
            }
        }
        with patch.object(sys, "argv", ["get.py", "--id", "CMP1", "--output", "json"]):
            assert getcmd.main() == 0
        client.get.assert_called_once_with("campaigns/CMP1")
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "CMP1"
    assert parsed["name"] == "Spring Sale"
