import sys
from contextlib import ExitStack
from unittest.mock import patch

from shopify.scripts.webhooks import delete as deletecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.webhooks.delete.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.webhooks.delete.ShopifyClient"))
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


def test_delete_webhook_dry_run_skips_graphql_without_yes(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_examplefixturetoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "delete.py",
                "--id",
                "gid://shopify/WebhookSubscription/1",
                "--dry-run",
            ],
        ):
            assert deletecmd.main() == 0
        assert client.graphql.call_count == 0
    out = capsys.readouterr().out
    assert "gid://shopify/WebhookSubscription/1" in out


def test_delete_webhook_without_yes_errors_in_live_mode(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_examplefixturetoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["delete.py", "--id", "gid://shopify/WebhookSubscription/1"],
        ):
            try:
                rc = deletecmd.main()
            except SystemExit as e:
                rc = e.code
        assert rc != 0
        assert client.graphql.call_count == 0


def test_delete_webhook_with_yes_calls_mutation(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_examplefixturetoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "webhookSubscriptionDelete": {
                "deletedWebhookSubscriptionId": "gid://shopify/WebhookSubscription/1",
                "userErrors": [],
            }
        }
        with patch.object(
            sys,
            "argv",
            ["delete.py", "--id", "gid://shopify/WebhookSubscription/1", "--yes"],
        ):
            assert deletecmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables == {"id": "gid://shopify/WebhookSubscription/1"}
    out = capsys.readouterr().out
    assert "Deleted: gid://shopify/WebhookSubscription/1" in out
