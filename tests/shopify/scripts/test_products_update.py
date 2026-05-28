import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from shopify.scripts.products import update as updatecmd
from shopify.utils.client import ShopifyUserError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.products.update.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.products.update.ShopifyClient"))
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


def test_update_dry_run_prints_input_and_does_not_call_graphql(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "update.py",
                "--id",
                "gid://shopify/Product/1",
                "--title",
                "New",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert updatecmd.main() == 0
        assert client.graphql.call_count == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["id"] == "gid://shopify/Product/1"
    assert parsed["title"] == "New"


def test_update_sends_only_provided_fields(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "productUpdate": {
                "product": {"id": "gid://shopify/Product/1", "title": "New", "status": "ACTIVE"},
                "userErrors": [],
            }
        }
        with patch.object(
            sys,
            "argv",
            ["update.py", "--id", "gid://shopify/Product/1", "--title", "New", "--output", "json"],
        ):
            assert updatecmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables == {"input": {"id": "gid://shopify/Product/1", "title": "New"}}


def test_update_sends_tags_as_list_and_descriptionHtml(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "productUpdate": {
                "product": {"id": "gid://shopify/Product/1", "title": "T", "status": "DRAFT"},
                "userErrors": [],
            }
        }
        with patch.object(
            sys,
            "argv",
            [
                "update.py",
                "--id",
                "gid://shopify/Product/1",
                "--status",
                "DRAFT",
                "--tags",
                "a,b,c",
                "--description-html",
                "<p>hi</p>",
                "--vendor",
                "Acme",
                "--output",
                "json",
            ],
        ):
            assert updatecmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        inp = variables["input"]
        assert inp["id"] == "gid://shopify/Product/1"
        assert inp["status"] == "DRAFT"
        assert inp["tags"] == ["a", "b", "c"]
        assert inp["descriptionHtml"] == "<p>hi</p>"
        assert inp["vendor"] == "Acme"
        # title NOT included
        assert "title" not in inp


def test_update_userErrors_raises(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "productUpdate": {
                "product": None,
                "userErrors": [{"field": ["title"], "message": "is too short"}],
            }
        }
        with (
            patch.object(
                sys,
                "argv",
                ["update.py", "--id", "gid://shopify/Product/1", "--title", "x"],
            ),
            pytest.raises(ShopifyUserError),
        ):
            updatecmd.main()
