import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.profiles import update as updatecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.profiles.update.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.profiles.update.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_update_dry_run_includes_id(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["update.py", "--id", "01H", "--first-name", "Ada", "--dry-run", "--output", "json"],
        ):
            assert updatecmd.main() == 0
        assert client.patch.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["id"] == "01H"
    assert parsed["data"]["type"] == "profile"
    assert parsed["data"]["attributes"]["first_name"] == "Ada"


def test_update_patches_path_with_id(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.patch.return_value = {
            "data": {"id": "01H", "type": "profile", "attributes": {"first_name": "Ada"}}
        }
        with patch.object(sys, "argv", ["update.py", "--id", "01H", "--first-name", "Ada"]):
            assert updatecmd.main() == 0
        args, kwargs = client.patch.call_args
        assert args[0] == "profiles/01H"
        body = kwargs.get("json") or args[1]
        assert body["data"]["id"] == "01H"
        assert body["data"]["attributes"]["first_name"] == "Ada"
