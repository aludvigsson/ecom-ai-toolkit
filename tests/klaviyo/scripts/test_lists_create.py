import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.lists import create as createcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.lists.create.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.lists.create.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_create_list_dry_run(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["create.py", "--name", "VIPs", "--dry-run", "--output", "json"]
        ):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "list"
    assert parsed["data"]["attributes"]["name"] == "VIPs"


def test_create_list_posts(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {
            "data": {"id": "LST9", "type": "list", "attributes": {"name": "VIPs"}}
        }
        with patch.object(sys, "argv", ["create.py", "--name", "VIPs"]):
            assert createcmd.main() == 0
        args, _ = client.post.call_args
        assert args[0] == "lists"
