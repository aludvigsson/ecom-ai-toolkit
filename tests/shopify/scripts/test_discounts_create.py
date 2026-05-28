import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from shopify.scripts.discounts import create as createcmd
from shopify.utils.client import ShopifyUserError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.discounts.create.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.discounts.create.ShopifyClient"))
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


def _variables_from_call(call_args):
    if len(call_args[0]) > 1:
        return call_args[0][1]
    return call_args[1].get("variables")


def test_create_percentage_code_discount_dry_run(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "create.py",
                "--kind",
                "percentage",
                "--code",
                "SPRING20",
                "--title",
                "Spring",
                "--value",
                "20",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert createcmd.main() == 0
        assert client.graphql.call_count == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["mutation"] == "discountCodeBasicCreate"
    assert parsed["code_or_automatic"] == "code"
    inp = parsed["input"]
    assert inp["title"] == "Spring"
    assert inp["code"] == "SPRING20"
    assert inp["customerGets"]["value"]["percentage"] == 0.20


def test_create_percentage_automatic_discount_dry_run(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "create.py",
                "--kind",
                "percentage",
                "--title",
                "Auto20",
                "--value",
                "20",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert createcmd.main() == 0
        assert client.graphql.call_count == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["mutation"] == "discountAutomaticBasicCreate"
    assert parsed["code_or_automatic"] == "automatic"
    inp = parsed["input"]
    assert inp["title"] == "Auto20"
    assert "code" not in inp
    assert inp["customerGets"]["value"]["percentage"] == 0.20


def test_create_fixed_amount_discount(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "discountCodeBasicCreate": {
                "codeDiscountNode": {"id": "gid://shopify/DiscountCodeNode/9"},
                "userErrors": [],
            }
        }
        with patch.object(
            sys,
            "argv",
            [
                "create.py",
                "--kind",
                "fixed",
                "--code",
                "FALL10",
                "--title",
                "Fall 10",
                "--value",
                "10.00",
                "--output",
                "json",
            ],
        ):
            assert createcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        inp = variables["basicCodeDiscount"]
        assert inp["code"] == "FALL10"
        amount = inp["customerGets"]["value"]["discountAmount"]
        assert amount["amount"] == "10.00"
        assert amount["appliesOnEachItem"] is False


def test_create_userErrors_raises(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "discountCodeBasicCreate": {
                "codeDiscountNode": None,
                "userErrors": [{"field": ["code"], "message": "is taken"}],
            }
        }
        with (
            patch.object(
                sys,
                "argv",
                [
                    "create.py",
                    "--kind",
                    "percentage",
                    "--code",
                    "DUP",
                    "--title",
                    "Dup",
                    "--value",
                    "10",
                ],
            ),
            pytest.raises(ShopifyUserError),
        ):
            createcmd.main()
