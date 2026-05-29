import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.templates import update as updatecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.templates.update.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.templates.update.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_update_template_dry_run_includes_id(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["update.py", "--id", "TPL1", "--name", "Welcome v2", "--dry-run", "--output", "json"],
        ):
            assert updatecmd.main() == 0
        assert client.patch.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["id"] == "TPL1"
    assert parsed["data"]["type"] == "template"
    assert parsed["data"]["attributes"]["name"] == "Welcome v2"


def test_update_template_patches_path(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.patch.return_value = {
            "data": {"id": "TPL1", "type": "template", "attributes": {"name": "Welcome v2"}}
        }
        with patch.object(sys, "argv", ["update.py", "--id", "TPL1", "--name", "Welcome v2"]):
            assert updatecmd.main() == 0
        args, _ = client.patch.call_args
        assert args[0] == "templates/TPL1"
