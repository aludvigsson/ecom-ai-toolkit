import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from klaviyo.scripts.campaigns import create as createcmd
from klaviyo.utils.client import KlaviyoAPIError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.campaigns.create.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.campaigns.create.KlaviyoClient"))
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
                "--name",
                "Spring Sale",
                "--list-id",
                "LST1",
                "--subject",
                "20% off",
                "--from-email",
                "hi@shop.com",
                "--from-label",
                "Shop",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "campaign"
    assert parsed["data"]["attributes"]["name"] == "Spring Sale"
    msg = parsed["data"]["attributes"]["campaign-messages"]["data"][0]
    assert msg["attributes"]["definition"]["channel"] == "email"
    assert msg["attributes"]["definition"]["content"]["subject"] == "20% off"
    audiences = parsed["data"]["attributes"]["audiences"]
    assert audiences["included"] == ["LST1"]


def test_create_posts_jsonapi_body(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {
            "data": {"id": "CMP9", "type": "campaign", "attributes": {"name": "Spring Sale"}}
        }
        with patch.object(
            sys,
            "argv",
            [
                "create.py",
                "--name",
                "Spring Sale",
                "--list-id",
                "LST1",
                "--subject",
                "20% off",
                "--from-email",
                "hi@shop.com",
                "--from-label",
                "Shop",
            ],
        ):
            assert createcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "campaigns"
        body = kwargs.get("json") or args[1]
        assert body["data"]["attributes"]["name"] == "Spring Sale"


def test_create_surfaces_api_error(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {
            "errors": [{"detail": "invalid audience", "source": {"pointer": "/data"}}]
        }
        with (
            patch.object(
                sys,
                "argv",
                [
                    "create.py",
                    "--name",
                    "Spring Sale",
                    "--list-id",
                    "LST1",
                    "--subject",
                    "x",
                    "--from-email",
                    "hi@shop.com",
                    "--from-label",
                    "Shop",
                ],
            ),
            pytest.raises(KlaviyoAPIError),
        ):
            createcmd.main()
