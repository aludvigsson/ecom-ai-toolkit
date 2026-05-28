import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from shopify.scripts.metafields import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.metafields.list.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.metafields.list.ShopifyClient"))
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


def test_list_metafields_for_product(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "product": {
                "metafields": {
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/Metafield/9",
                                "namespace": "custom",
                                "key": "color",
                                "type": "single_line_text_field",
                                "value": "blue",
                            }
                        }
                    ]
                }
            }
        }
        with patch.object(
            sys,
            "argv",
            [
                "list.py",
                "--owner-type",
                "PRODUCT",
                "--owner-id",
                "gid://shopify/Product/1",
                "--output",
                "json",
            ],
        ):
            assert listcmd.main() == 0
        query, variables = _query_and_vars(client.graphql.call_args)
        assert "product(id: $id)" in query
        assert variables == {
            "first": 50,
            "namespace": None,
            "key": None,
            "id": "gid://shopify/Product/1",
        }


def test_list_metafields_for_shop_does_not_require_id(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {"shop": {"metafields": {"edges": []}}}
        with patch.object(
            sys,
            "argv",
            ["list.py", "--owner-type", "SHOP", "--output", "json"],
        ):
            assert listcmd.main() == 0
        query, variables = _query_and_vars(client.graphql.call_args)
        assert "shop {" in query
        assert "id" not in variables
        assert variables == {"first": 50, "namespace": None, "key": None}


def test_list_metafields_non_shop_owner_without_id_errors(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with (
        patch.object(sys, "argv", ["list.py", "--owner-type", "PRODUCT"]),
        pytest.raises(SystemExit),
    ):
        listcmd.main()
