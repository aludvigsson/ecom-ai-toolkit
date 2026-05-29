import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from klaviyo.scripts.profiles import create as createcmd
from klaviyo.utils.client import KlaviyoAPIError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.profiles.create.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.profiles.create.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_create_dry_run_prints_body_and_skips_post(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "create.py",
                "--email",
                "a@b.com",
                "--first-name",
                "Ada",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "profile"
    assert parsed["data"]["attributes"]["email"] == "a@b.com"
    assert parsed["data"]["attributes"]["first_name"] == "Ada"


def test_create_posts_jsonapi_body(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {
            "data": {"id": "01H", "type": "profile", "attributes": {"email": "a@b.com"}}
        }
        with patch.object(sys, "argv", ["create.py", "--email", "a@b.com"]):
            assert createcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "profiles"
        body = kwargs.get("json") or args[1]
        assert body["data"]["attributes"]["email"] == "a@b.com"


def test_create_surfaces_api_error(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {
            "errors": [{"detail": "duplicate profile", "source": {"pointer": "/data"}}]
        }
        with (
            patch.object(sys, "argv", ["create.py", "--email", "a@b.com"]),
            pytest.raises(KlaviyoAPIError),
        ):
            createcmd.main()
