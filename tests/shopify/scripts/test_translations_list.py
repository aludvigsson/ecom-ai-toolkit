import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from shopify.scripts.translations import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.translations.list.load_config"))
    mock_client_class = stack.enter_context(
        patch("shopify.scripts.translations.list.ShopifyClient")
    )
    mock_cfg.return_value.store.shopify_domain = "x.myshopify.com"
    mock_cfg.return_value.domains = {
        "shopify": type("D", (), {"api_version": "2025-10", "enabled": True})()
    }
    mock_client_instance = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, mock_client_instance


def _query_and_vars(call_args):
    args = call_args[0]
    kwargs = call_args[1]
    query = args[0]
    variables = args[1] if len(args) > 1 else kwargs.get("variables")
    return query, variables


def test_list_translations_for_resource_id(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "translatableResource": {
                "resourceId": "gid://shopify/Product/1",
                "translatableContent": [
                    {
                        "key": "title",
                        "value": "Hello",
                        "digest": "abc123",
                        "locale": "en",
                    }
                ],
                "translations": [
                    {"key": "title", "locale": "sv-SE", "value": "Hej"},
                ],
            }
        }
        with patch.object(
            sys,
            "argv",
            [
                "list.py",
                "--resource-id",
                "gid://shopify/Product/1",
                "--locale",
                "sv-SE",
                "--output",
                "json",
            ],
        ):
            assert listcmd.main() == 0
        query, variables = _query_and_vars(client.graphql.call_args)
        assert "translatableResource(resourceId: $resourceId)" in query
        assert variables == {
            "resourceId": "gid://shopify/Product/1",
            "locale": "sv-SE",
        }


def test_list_translations_by_resource_type_sweep(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "translatableResources": {
                "edges": [
                    {
                        "node": {
                            "resourceId": "gid://shopify/Product/1",
                            "translatableContent": [
                                {
                                    "key": "title",
                                    "value": "Hello",
                                    "digest": "abc",
                                    "locale": "en",
                                }
                            ],
                            "translations": [
                                {"key": "title", "locale": "sv-SE", "value": "Hej"},
                            ],
                        }
                    },
                    {
                        "node": {
                            "resourceId": "gid://shopify/Product/2",
                            "translatableContent": [
                                {
                                    "key": "title",
                                    "value": "World",
                                    "digest": "def",
                                    "locale": "en",
                                }
                            ],
                            "translations": [],
                        }
                    },
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
        with patch.object(
            sys,
            "argv",
            [
                "list.py",
                "--resource-type",
                "PRODUCT",
                "--locale",
                "sv-SE",
                "--output",
                "json",
            ],
        ):
            assert listcmd.main() == 0
        query, variables = _query_and_vars(client.graphql.call_args)
        assert "translatableResources(first: $first, resourceType: $resourceType" in query
        assert variables == {
            "first": 50,
            "resourceType": "PRODUCT",
            "locale": "sv-SE",
        }


def test_list_translations_neither_id_nor_type_errors(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with (
        patch.object(sys, "argv", ["list.py", "--locale", "sv-SE"]),
        pytest.raises(SystemExit),
    ):
        listcmd.main()
