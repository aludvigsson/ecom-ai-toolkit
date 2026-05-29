import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.templates import render as rendercmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.templates.render.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.templates.render.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_render_dry_run_builds_body(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "render.py",
                "--id",
                "TPL1",
                "--context",
                '{"first_name": "Ada"}',
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert rendercmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "template"
    assert parsed["data"]["id"] == "TPL1"
    assert parsed["data"]["attributes"]["context"] == {"first_name": "Ada"}


def test_render_posts_to_template_render(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {
            "data": {"id": "TPL1", "type": "template", "attributes": {"html": "<h1>Hi Ada</h1>"}}
        }
        with patch.object(
            sys, "argv", ["render.py", "--id", "TPL1", "--context", '{"first_name": "Ada"}']
        ):
            assert rendercmd.main() == 0
        args, _ = client.post.call_args
        assert args[0] == "template-render"
