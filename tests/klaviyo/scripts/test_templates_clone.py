import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.templates import clone as clonecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.templates.clone.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.templates.clone.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_clone_dry_run_builds_body(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "clone.py",
                "--id",
                "TPL1",
                "--name",
                "Welcome (copy)",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert clonecmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "template"
    assert parsed["data"]["id"] == "TPL1"
    assert parsed["data"]["attributes"]["name"] == "Welcome (copy)"


def test_clone_posts_to_template_clone(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {
            "data": {"id": "TPL2", "type": "template", "attributes": {"name": "Welcome (copy)"}}
        }
        with patch.object(sys, "argv", ["clone.py", "--id", "TPL1", "--name", "Welcome (copy)"]):
            assert clonecmd.main() == 0
        args, _ = client.post.call_args
        assert args[0] == "template-clone"
