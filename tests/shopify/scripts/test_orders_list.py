import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from shopify.scripts.orders import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.orders.list.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.orders.list.ShopifyClient"))
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


def test_list_orders_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "orders": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Order/1",
                            "name": "#1001",
                            "createdAt": "2026-05-15T10:00:00Z",
                            "displayFinancialStatus": "PAID",
                            "displayFulfillmentStatus": "FULFILLED",
                            "currentTotalPriceSet": {
                                "shopMoney": {"amount": "499.00", "currencyCode": "SEK"}
                            },
                            "customer": {
                                "id": "gid://shopify/Customer/1",
                                "email": "a@b.com",
                                "displayName": "A B",
                            },
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
    assert parsed[0]["name"] == "#1001"
    assert parsed[0]["total"] == "499.00"
    assert parsed[0]["currency"] == "SEK"
    assert parsed[0]["customer_email"] == "a@b.com"


def test_list_orders_composes_date_range(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "orders": {"edges": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}
        }
        with patch.object(sys, "argv", ["list.py", "--from", "2026-05-01", "--to", "2026-05-31"]):
            assert listcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables["query"] == "created_at:>=2026-05-01 created_at:<=2026-05-31"


def test_list_orders_composes_financial_and_email(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "orders": {"edges": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}
        }
        with patch.object(
            sys,
            "argv",
            ["list.py", "--financial", "paid", "--customer-email", "x@y.com"],
        ):
            assert listcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables["query"] == "financial_status:paid email:x@y.com"
