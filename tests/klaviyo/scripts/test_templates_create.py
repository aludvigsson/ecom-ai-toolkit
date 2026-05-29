import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.templates import create as createcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.templates.create.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.templates.create.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_create_template_dry_run_with_inline_html(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "create.py",
                "--name",
                "Welcome",
                "--html",
                "<h1>Hi</h1>",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "template"
    assert parsed["data"]["attributes"]["name"] == "Welcome"
    assert parsed["data"]["attributes"]["html"] == "<h1>Hi</h1>"


def test_create_template_reads_html_file(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    html_file = tmp_path / "t.html"
    html_file.write_text("<p>from file</p>")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "create.py",
                "--name",
                "Welcome",
                "--html-file",
                str(html_file),
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert createcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["attributes"]["html"] == "<p>from file</p>"


def test_create_template_posts(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {
            "data": {"id": "TPL9", "type": "template", "attributes": {"name": "Welcome"}}
        }
        with patch.object(sys, "argv", ["create.py", "--name", "Welcome", "--html", "<h1>Hi</h1>"]):
            assert createcmd.main() == 0
        args, _ = client.post.call_args
        assert args[0] == "templates"
