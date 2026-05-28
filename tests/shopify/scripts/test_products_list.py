import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from shopify.scripts.products import list as listcmd


def _setup_mocks(stack):
    """Returns (mock_cfg, mock_client_class, mock_client_instance)."""
    mock_cfg = stack.enter_context(patch("shopify.scripts.products.list.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.products.list.ShopifyClient"))
    mock_cfg.return_value.store.shopify_domain = "x.myshopify.com"
    mock_cfg.return_value.domains = {
        "shopify": type("D", (), {"api_version": "2025-10", "enabled": True})()
    }
    mock_client_instance = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, mock_client_instance


def _variables_from_call(call_args):
    """Pull variables out of either positional or kw call shape."""
    if len(call_args[0]) > 1:
        return call_args[0][1]
    return call_args[1].get("variables")


def test_list_products_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "products": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Product/1",
                            "title": "Pearl",
                            "handle": "pearl",
                            "status": "ACTIVE",
                            "vendor": "Acme",
                            "totalInventory": 12,
                        }
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
        with patch.object(sys, "argv", ["list.py", "--output", "json", "--limit", "10"]):
            assert listcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables == {"first": 10, "query": None}
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed[0]["title"] == "Pearl"


def test_list_products_composes_query_from_status_and_vendor(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "products": {"edges": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}
        }
        with patch.object(sys, "argv", ["list.py", "--status", "ACTIVE", "--vendor", "Acme"]):
            assert listcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables["query"] == "status:active vendor:'Acme'"


def test_list_products_query_composes_tag_and_raw(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "products": {"edges": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}
        }
        with patch.object(sys, "argv", ["list.py", "--tag", "launch", "--query", "title:*pearl*"]):
            assert listcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables["query"] == "tag:'launch' title:*pearl*"
