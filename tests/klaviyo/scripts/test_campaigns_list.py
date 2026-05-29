import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.campaigns import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.campaigns.list.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.campaigns.list.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_campaigns_list_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [
                {
                    "id": "CMP1",
                    "type": "campaign",
                    "attributes": {"name": "Spring Sale", "status": "Draft"},
                }
            ]
        )
        with patch.object(sys, "argv", ["list.py", "--output", "json"]):
            assert listcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "CMP1"
    assert parsed[0]["name"] == "Spring Sale"
    assert parsed[0]["status"] == "Draft"


def test_campaigns_list_default_channel_filter(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py"]):
            assert listcmd.main() == 0
        _, kwargs = client.paginate.call_args
        assert kwargs["params"]["filter"] == 'equals(messages.channel,"email")'


def test_campaigns_list_channel_override(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py", "--channel", "sms"]):
            assert listcmd.main() == 0
        _, kwargs = client.paginate.call_args
        assert kwargs["params"]["filter"] == 'equals(messages.channel,"sms")'
        assert kwargs["limit"] == 50
