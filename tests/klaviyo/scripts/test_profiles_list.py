import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.profiles import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.profiles.list.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.profiles.list.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_profiles_list_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [
                {
                    "id": "01H",
                    "type": "profile",
                    "attributes": {
                        "email": "a@b.com",
                        "first_name": "Ada",
                        "last_name": "Lovelace",
                    },
                }
            ]
        )
        with patch.object(sys, "argv", ["list.py", "--output", "json"]):
            assert listcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "01H"
    assert parsed[0]["email"] == "a@b.com"
    assert parsed[0]["first_name"] == "Ada"


def test_profiles_list_email_filter_builds_param(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py", "--email", "a@b.com"]):
            assert listcmd.main() == 0
        _, kwargs = client.paginate.call_args
        params = kwargs.get("params") or client.paginate.call_args[0][1]
        assert params["filter"] == 'equals(email,"a@b.com")'


def test_profiles_list_passes_limit(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py", "--limit", "5"]):
            assert listcmd.main() == 0
        _, kwargs = client.paginate.call_args
        assert kwargs["limit"] == 5
