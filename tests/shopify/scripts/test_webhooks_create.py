import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from shopify.scripts.webhooks import create as createcmd
from shopify.utils.client import ShopifyUserError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.webhooks.create.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.webhooks.create.ShopifyClient"))
    mock_cfg.return_value.store.shopify_domain = "example-store.myshopify.com"
    mock_cfg.return_value.domains = {
        "shopify": type("D", (), {"api_version": "2025-10", "enabled": True})()
    }
    mock_client_instance = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, mock_client_instance


def _variables_from_call(call_args):
    if len(call_args[0]) > 1:
        return call_args[0][1]
    return call_args[1].get("variables")


def test_create_webhook_dry_run_prints_input_and_skips_graphql(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_examplefixturetoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "create.py",
                "--topic",
                "ORDERS_CREATE",
                "--callback-url",
                "https://example.com/webhooks/orders/create",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert createcmd.main() == 0
        assert client.graphql.call_count == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["topic"] == "ORDERS_CREATE"
    assert parsed["input"]["callbackUrl"] == "https://example.com/webhooks/orders/create"
    assert parsed["input"]["format"] == "JSON"


def test_create_webhook_default_json_format(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_examplefixturetoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "webhookSubscriptionCreate": {
                "webhookSubscription": {
                    "id": "gid://shopify/WebhookSubscription/1",
                    "topic": "ORDERS_CREATE",
                    "format": "JSON",
                },
                "userErrors": [],
            }
        }
        with patch.object(
            sys,
            "argv",
            [
                "create.py",
                "--topic",
                "ORDERS_CREATE",
                "--callback-url",
                "https://example.com/webhooks/orders/create",
            ],
        ):
            assert createcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables["topic"] == "ORDERS_CREATE"
        assert variables["input"]["format"] == "JSON"
        assert variables["input"]["callbackUrl"] == "https://example.com/webhooks/orders/create"


def test_create_webhook_rejects_non_https_callback(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_examplefixturetoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with (
            patch.object(
                sys,
                "argv",
                [
                    "create.py",
                    "--topic",
                    "ORDERS_CREATE",
                    "--callback-url",
                    "http://example.com/webhooks/orders/create",
                ],
            ),
            pytest.raises(SystemExit),
        ):
            createcmd.main()
        assert client.graphql.call_count == 0


def test_create_webhook_userErrors_raises(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_examplefixturetoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "webhookSubscriptionCreate": {
                "webhookSubscription": None,
                "userErrors": [{"field": ["callbackUrl"], "message": "is invalid"}],
            }
        }
        with (
            patch.object(
                sys,
                "argv",
                [
                    "create.py",
                    "--topic",
                    "ORDERS_CREATE",
                    "--callback-url",
                    "https://example.com/webhooks/orders/create",
                ],
            ),
            pytest.raises(ShopifyUserError),
        ):
            createcmd.main()
