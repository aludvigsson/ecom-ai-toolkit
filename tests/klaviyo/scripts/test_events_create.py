import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from klaviyo.scripts.events import create as createcmd
from klaviyo.utils.client import KlaviyoAPIError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.events.create.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.events.create.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_create_dry_run_builds_body_and_skips_post(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "create.py",
                "--metric-name",
                "Viewed Demo",
                "--email",
                "a@b.com",
                "--properties",
                '{"plan": "pro"}',
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "event"
    attrs = parsed["data"]["attributes"]
    assert attrs["metric"]["data"]["attributes"]["name"] == "Viewed Demo"
    assert attrs["profile"]["data"]["attributes"]["email"] == "a@b.com"
    assert attrs["properties"] == {"plan": "pro"}


def test_create_posts_to_events_endpoint(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {}
        with patch.object(
            sys, "argv", ["create.py", "--metric-name", "Viewed Demo", "--email", "a@b.com"]
        ):
            assert createcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "events"
        body = kwargs.get("json") or args[1]
        assert body["data"]["attributes"]["metric"]["data"]["attributes"]["name"] == "Viewed Demo"


def test_create_invalid_properties_json_errors(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["create.py", "--metric-name", "X", "--email", "a@b.com", "--properties", "not-json"],
        ):
            try:
                createcmd.main()
            except SystemExit as exc:
                assert exc.code != 0
            else:
                raise AssertionError("expected SystemExit")


def test_create_surfaces_api_error(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"errors": [{"detail": "bad metric"}]}
        with (
            patch.object(sys, "argv", ["create.py", "--metric-name", "X", "--email", "a@b.com"]),
            pytest.raises(KlaviyoAPIError),
        ):
            createcmd.main()
