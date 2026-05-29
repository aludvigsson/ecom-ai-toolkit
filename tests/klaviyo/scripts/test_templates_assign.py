import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.templates import assign as assigncmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.templates.assign.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.templates.assign.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_assign_dry_run_builds_body(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "assign.py",
                "--message-id",
                "MSG1",
                "--template-id",
                "TPL1",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert assigncmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "campaign-message"
    assert parsed["data"]["id"] == "MSG1"
    rel = parsed["data"]["relationships"]["template"]["data"]
    assert rel["type"] == "template"
    assert rel["id"] == "TPL1"


def test_assign_posts_to_endpoint(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"data": {"id": "MSG1", "type": "campaign-message"}}
        with patch.object(
            sys, "argv", ["assign.py", "--message-id", "MSG1", "--template-id", "TPL1"]
        ):
            assert assigncmd.main() == 0
        args, _ = client.post.call_args
        assert args[0] == "campaign-message-assign-template"
