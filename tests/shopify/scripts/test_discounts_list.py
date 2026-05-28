import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from shopify.scripts.discounts import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.discounts.list.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.discounts.list.ShopifyClient"))
    mock_cfg.return_value.store.shopify_domain = "x.myshopify.com"
    mock_cfg.return_value.domains = {
        "shopify": type("D", (), {"api_version": "2025-10", "enabled": True})()
    }
    mock_client_instance = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, mock_client_instance


def _code_response(title="Spring", code="SPRING20", status="ACTIVE"):
    return {
        "codeDiscountNodes": {
            "edges": [
                {
                    "node": {
                        "id": "gid://shopify/DiscountCodeNode/1",
                        "codeDiscount": {
                            "__typename": "DiscountCodeBasic",
                            "title": title,
                            "summary": "20% off",
                            "status": status,
                            "startsAt": "2026-03-01T00:00:00Z",
                            "endsAt": "2026-03-31T23:59:59Z",
                            "codes": {"edges": [{"node": {"code": code}}]},
                        },
                    }
                }
            ],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }
    }


def _automatic_response(title="Auto", status="ACTIVE"):
    return {
        "automaticDiscountNodes": {
            "edges": [
                {
                    "node": {
                        "id": "gid://shopify/DiscountAutomaticNode/2",
                        "automaticDiscount": {
                            "__typename": "DiscountAutomaticBasic",
                            "title": title,
                            "summary": "Free shipping",
                            "status": status,
                            "startsAt": "2026-03-01T00:00:00Z",
                            "endsAt": None,
                        },
                    }
                }
            ],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }
    }


def test_list_code_discounts(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = _code_response()
        with patch.object(sys, "argv", ["list.py", "--type", "code", "--output", "json"]):
            assert listcmd.main() == 0
        assert client.graphql.call_count == 1
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert len(parsed) == 1
    assert parsed[0]["code"] == "SPRING20"
    assert parsed[0]["kind"] == "DiscountCodeBasic"
    assert parsed[0]["title"] == "Spring"


def test_list_automatic_discounts(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = _automatic_response()
        with patch.object(sys, "argv", ["list.py", "--type", "automatic", "--output", "json"]):
            assert listcmd.main() == 0
        assert client.graphql.call_count == 1
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert len(parsed) == 1
    assert parsed[0]["code"] is None
    assert parsed[0]["kind"] == "DiscountAutomaticBasic"
    assert parsed[0]["title"] == "Auto"


def test_list_all_runs_both_queries(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [_code_response(), _automatic_response()]
        with patch.object(sys, "argv", ["list.py", "--type", "all", "--output", "json"]):
            assert listcmd.main() == 0
        assert client.graphql.call_count == 2
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert len(parsed) == 2
    titles = {p["title"] for p in parsed}
    assert titles == {"Spring", "Auto"}


def test_list_status_filter_post_query(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    response = {
        "codeDiscountNodes": {
            "edges": [
                {
                    "node": {
                        "id": "gid://shopify/DiscountCodeNode/1",
                        "codeDiscount": {
                            "__typename": "DiscountCodeBasic",
                            "title": "A",
                            "summary": "",
                            "status": "ACTIVE",
                            "startsAt": "2026-03-01T00:00:00Z",
                            "endsAt": None,
                            "codes": {"edges": [{"node": {"code": "A"}}]},
                        },
                    }
                },
                {
                    "node": {
                        "id": "gid://shopify/DiscountCodeNode/2",
                        "codeDiscount": {
                            "__typename": "DiscountCodeBasic",
                            "title": "B",
                            "summary": "",
                            "status": "ACTIVE",
                            "startsAt": "2026-03-01T00:00:00Z",
                            "endsAt": None,
                            "codes": {"edges": [{"node": {"code": "B"}}]},
                        },
                    }
                },
                {
                    "node": {
                        "id": "gid://shopify/DiscountCodeNode/3",
                        "codeDiscount": {
                            "__typename": "DiscountCodeBasic",
                            "title": "C",
                            "summary": "",
                            "status": "EXPIRED",
                            "startsAt": "2025-01-01T00:00:00Z",
                            "endsAt": "2025-12-31T23:59:59Z",
                            "codes": {"edges": [{"node": {"code": "C"}}]},
                        },
                    }
                },
            ],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }
    }
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = response
        with patch.object(
            sys,
            "argv",
            ["list.py", "--type", "code", "--status", "ACTIVE", "--output", "json"],
        ):
            assert listcmd.main() == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert len(parsed) == 2
    assert {p["title"] for p in parsed} == {"A", "B"}
