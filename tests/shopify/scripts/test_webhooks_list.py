import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from shopify.scripts.webhooks import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.webhooks.list.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.webhooks.list.ShopifyClient"))
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


def test_list_webhooks_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_examplefixturetoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "webhookSubscriptions": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/WebhookSubscription/1",
                            "topic": "ORDERS_CREATE",
                            "format": "JSON",
                            "createdAt": "2026-05-01T10:00:00Z",
                            "updatedAt": "2026-05-01T10:00:00Z",
                            "endpoint": {
                                "__typename": "WebhookHttpEndpoint",
                                "callbackUrl": "https://example.com/webhooks/orders/create",
                            },
                        }
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
        with patch.object(sys, "argv", ["list.py", "--output", "json"]):
            assert listcmd.main() == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed[0]["id"] == "gid://shopify/WebhookSubscription/1"
    assert parsed[0]["topic"] == "ORDERS_CREATE"
    assert parsed[0]["endpoint_kind"] == "WebhookHttpEndpoint"
    assert parsed[0]["endpoint_target"] == "https://example.com/webhooks/orders/create"


def test_list_webhooks_filter_by_topic(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_examplefixturetoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "webhookSubscriptions": {
                "edges": [],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
        with patch.object(sys, "argv", ["list.py", "--topic", "ORDERS_CREATE"]):
            assert listcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables["topics"] == ["ORDERS_CREATE"]


def test_list_webhooks_handles_eventbridge_endpoint(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_examplefixturetoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "webhookSubscriptions": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/WebhookSubscription/2",
                            "topic": "PRODUCTS_UPDATE",
                            "format": "JSON",
                            "createdAt": "2026-05-01T10:00:00Z",
                            "updatedAt": "2026-05-01T10:00:00Z",
                            "endpoint": {
                                "__typename": "WebhookEventBridgeEndpoint",
                                "arn": "arn:aws:events:us-east-1:123456789012:event-bus/example",
                            },
                        }
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
        with patch.object(sys, "argv", ["list.py", "--output", "json"]):
            assert listcmd.main() == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed[0]["endpoint_kind"] == "WebhookEventBridgeEndpoint"
    assert parsed[0]["endpoint_target"] == "arn:aws:events:us-east-1:123456789012:event-bus/example"
