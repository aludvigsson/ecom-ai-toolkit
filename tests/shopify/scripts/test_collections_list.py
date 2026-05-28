import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from shopify.scripts.collections import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.collections.list.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.collections.list.ShopifyClient"))
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


def test_list_collections_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "collections": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Collection/1",
                            "title": "Summer",
                            "handle": "summer",
                            "productsCount": {"count": 12},
                            "sortOrder": "MANUAL",
                            "updatedAt": "2025-01-01T00:00:00Z",
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
    assert parsed[0]["title"] == "Summer"
    assert parsed[0]["handle"] == "summer"
    assert parsed[0]["productsCount"] == 12


def test_list_collections_filter_smart(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "collections": {"edges": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}
        }
        with patch.object(sys, "argv", ["list.py", "--type", "smart"]):
            assert listcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables["query"] == "collection_type:smart"


def test_list_collections_filter_custom_with_raw_query(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "collections": {"edges": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}
        }
        with patch.object(sys, "argv", ["list.py", "--type", "custom", "--query", "title:summer*"]):
            assert listcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables["query"] == "collection_type:custom title:summer*"
