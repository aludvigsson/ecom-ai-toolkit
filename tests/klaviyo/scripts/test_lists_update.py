import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.lists import update as updatecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.lists.update.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.lists.update.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_update_list_dry_run_includes_id(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["update.py", "--id", "LST1", "--name", "VIP", "--dry-run", "--output", "json"],
        ):
            assert updatecmd.main() == 0
        assert client.patch.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["id"] == "LST1"
    assert parsed["data"]["attributes"]["name"] == "VIP"


def test_update_list_patches_path(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.patch.return_value = {
            "data": {"id": "LST1", "type": "list", "attributes": {"name": "VIP"}}
        }
        with patch.object(sys, "argv", ["update.py", "--id", "LST1", "--name", "VIP"]):
            assert updatecmd.main() == 0
        args, _ = client.patch.call_args
        assert args[0] == "lists/LST1"
