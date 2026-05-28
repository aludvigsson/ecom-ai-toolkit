import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from shopify.scripts.discounts import update as updatecmd
from shopify.utils.client import ShopifyUserError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.discounts.update.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.discounts.update.ShopifyClient"))
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


def _detect_code_basic():
    return {
        "codeDiscountNode": {"codeDiscount": {"__typename": "DiscountCodeBasic"}},
        "automaticDiscountNode": None,
    }


def _detect_automatic_basic():
    return {
        "codeDiscountNode": None,
        "automaticDiscountNode": {"automaticDiscount": {"__typename": "DiscountAutomaticBasic"}},
    }


def test_update_detects_code_basic_and_dispatches_to_correct_mutation(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            _detect_code_basic(),
            {
                "discountCodeBasicUpdate": {
                    "codeDiscountNode": {"id": "gid://shopify/DiscountCodeNode/1"},
                    "userErrors": [],
                }
            },
        ]
        with patch.object(
            sys,
            "argv",
            [
                "update.py",
                "--id",
                "gid://shopify/DiscountCodeNode/1",
                "--ends-at",
                "2026-12-31T23:59:59Z",
                "--output",
                "json",
            ],
        ):
            assert updatecmd.main() == 0
        assert client.graphql.call_count == 2
        second_call_query = _query_from_call(client.graphql.call_args_list[1])
        assert "discountCodeBasicUpdate" in second_call_query


def test_update_dry_run_runs_detect_but_skips_update(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = _detect_automatic_basic()
        with patch.object(
            sys,
            "argv",
            [
                "update.py",
                "--id",
                "gid://shopify/DiscountAutomaticNode/2",
                "--title",
                "New title",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert updatecmd.main() == 0
        assert client.graphql.call_count == 1


def test_update_value_without_applies_to_errors(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    # parser.error -> SystemExit before any network call.
    with (
        patch.object(
            sys,
            "argv",
            [
                "update.py",
                "--id",
                "gid://shopify/DiscountCodeNode/1",
                "--value",
                "25",
            ],
        ),
        pytest.raises(SystemExit),
    ):
        updatecmd.main()


def test_update_userErrors_raises(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            _detect_code_basic(),
            {
                "discountCodeBasicUpdate": {
                    "codeDiscountNode": None,
                    "userErrors": [{"field": ["title"], "message": "is invalid"}],
                }
            },
        ]
        with (
            patch.object(
                sys,
                "argv",
                [
                    "update.py",
                    "--id",
                    "gid://shopify/DiscountCodeNode/1",
                    "--title",
                    "x",
                ],
            ),
            pytest.raises(ShopifyUserError),
        ):
            updatecmd.main()
