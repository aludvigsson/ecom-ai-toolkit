import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from shopify.scripts.products import get as getcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.products.get.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.products.get.ShopifyClient"))
    mock_cfg.return_value.store.shopify_domain = "x.myshopify.com"
    mock_cfg.return_value.domains = {
        "shopify": type("D", (), {"api_version": "2025-10", "enabled": True})()
    }
    mock_client_instance = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, mock_client_instance


def _variables_from_call(call_args):
    if len(call_args[0]) > 1:
        return call_args[0][1]
    return call_args[1].get("variables")


_FAKE_PRODUCT = {
    "product": {
        "id": "gid://shopify/Product/1",
        "title": "Pearl",
        "handle": "pearl",
        "status": "ACTIVE",
        "vendor": "Acme",
        "productType": "Jewelry",
        "tags": ["a"],
        "variants": {"edges": []},
        "metafields": {"edges": []},
        "translations": [],
    }
}


def test_get_by_id_calls_graphql_with_id(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = _FAKE_PRODUCT
        with patch.object(
            sys, "argv", ["get.py", "--id", "gid://shopify/Product/1", "--output", "json"]
        ):
            assert getcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables["id"] == "gid://shopify/Product/1"
        assert variables["handle"] is None


def test_get_by_handle_calls_graphql_with_handle(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = _FAKE_PRODUCT
        with patch.object(sys, "argv", ["get.py", "--handle", "pearl", "--output", "json"]):
            assert getcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables["handle"] == "pearl"
        assert variables["id"] is None


def test_neither_id_nor_handle_errors(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with patch.object(sys, "argv", ["get.py"]), pytest.raises(SystemExit):
        getcmd.main()


def test_both_id_and_handle_errors(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with (
        patch.object(
            sys, "argv", ["get.py", "--id", "gid://shopify/Product/1", "--handle", "pearl"]
        ),
        pytest.raises(SystemExit),
    ):
        getcmd.main()


def test_locale_is_passed_through_when_provided(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = _FAKE_PRODUCT
        with patch.object(
            sys, "argv", ["get.py", "--handle", "pearl", "--locale", "sv", "--output", "json"]
        ):
            assert getcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables["locale"] == "sv"
