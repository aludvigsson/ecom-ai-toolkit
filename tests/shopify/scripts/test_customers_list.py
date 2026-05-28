import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from shopify.scripts.customers import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.customers.list.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.customers.list.ShopifyClient"))
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


def _customer_node(idx: int, num_orders: int, email: str = "x@y.com") -> dict:
    return {
        "id": f"gid://shopify/Customer/{idx}",
        "email": email,
        "displayName": f"User {idx}",
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-05-01T00:00:00Z",
        "numberOfOrders": num_orders,
        "amountSpent": {"amount": f"{num_orders * 100}.00", "currencyCode": "SEK"},
        "tags": ["vip", "newsletter"],
        "state": "ENABLED",
    }


def test_list_customers_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "customers": {
                "edges": [{"node": _customer_node(1, 3, "alice@example.com")}],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
        with patch.object(sys, "argv", ["list.py", "--output", "json", "--limit", "10"]):
            assert listcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables == {"first": 10, "query": None}
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed[0]["email"] == "alice@example.com"
    assert parsed[0]["total_spent"] == "300.00"
    assert parsed[0]["currency"] == "SEK"
    assert parsed[0]["numberOfOrders"] == 3
    assert parsed[0]["tags"] == ["vip", "newsletter"]


def test_list_customers_composes_email_and_tag_filters(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "customers": {
                "edges": [],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
        with patch.object(
            sys,
            "argv",
            ["list.py", "--email", "alice@example.com", "--tag", "vip"],
        ):
            assert listcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables["query"] == "email:alice@example.com tag:'vip'"


def test_list_customers_state_filter(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "customers": {
                "edges": [],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
        with patch.object(sys, "argv", ["list.py", "--state", "enabled"]):
            assert listcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables["query"] == "state:enabled"


def test_list_customers_min_orders_filters_post_query(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "customers": {
                "edges": [
                    {"node": _customer_node(1, 2, "a@a.com")},
                    {"node": _customer_node(2, 5, "b@b.com")},
                    {"node": _customer_node(3, 10, "c@c.com")},
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
        with patch.object(sys, "argv", ["list.py", "--min-orders", "5", "--output", "json"]):
            assert listcmd.main() == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert len(parsed) == 2
    emails = sorted(r["email"] for r in parsed)
    assert emails == ["b@b.com", "c@c.com"]
