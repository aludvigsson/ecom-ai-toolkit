import sys
from contextlib import ExitStack
from unittest.mock import patch

from shopify.scripts.discounts import delete as deletecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.discounts.delete.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.discounts.delete.ShopifyClient"))
    mock_cfg.return_value.store.shopify_domain = "x.myshopify.com"
    mock_cfg.return_value.domains = {
        "shopify": type("D", (), {"api_version": "2025-10", "enabled": True})()
    }
    mock_client_instance = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, mock_client_instance


def _query_from_call(call_args):
    if len(call_args[0]) >= 1:
        return call_args[0][0]
    return call_args[1].get("query")


def _detect_code():
    return {
        "codeDiscountNode": {"codeDiscount": {"__typename": "DiscountCodeBasic"}},
        "automaticDiscountNode": None,
    }


def _detect_automatic():
    return {
        "codeDiscountNode": None,
        "automaticDiscountNode": {"automaticDiscount": {"__typename": "DiscountAutomaticBasic"}},
    }


def test_delete_dry_run_runs_detect_skips_delete(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = _detect_code()
        with patch.object(
            sys,
            "argv",
            [
                "delete.py",
                "--id",
                "gid://shopify/DiscountCodeNode/1",
                "--dry-run",
            ],
        ):
            assert deletecmd.main() == 0
        assert client.graphql.call_count == 1
    out = capsys.readouterr().out
    assert "gid://shopify/DiscountCodeNode/1" in out


def test_delete_without_yes_errors(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["delete.py", "--id", "gid://shopify/DiscountCodeNode/1"],
        ):
            try:
                rc = deletecmd.main()
            except SystemExit as e:
                rc = e.code
        assert rc != 0
        assert client.graphql.call_count == 0


def test_delete_with_yes_calls_delete_mutation(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            _detect_automatic(),
            {
                "discountAutomaticDelete": {
                    "deletedAutomaticDiscountId": "gid://shopify/DiscountAutomaticNode/9",
                    "userErrors": [],
                }
            },
        ]
        with patch.object(
            sys,
            "argv",
            [
                "delete.py",
                "--id",
                "gid://shopify/DiscountAutomaticNode/9",
                "--yes",
            ],
        ):
            assert deletecmd.main() == 0
        assert client.graphql.call_count == 2
        second_query = _query_from_call(client.graphql.call_args_list[1])
        assert "discountAutomaticDelete" in second_query
