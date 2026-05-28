import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from shopify.scripts.collection import update as updatecmd
from shopify.utils.client import ShopifyUserError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.collection.update.load_config"))
    mock_client_class = stack.enter_context(
        patch("shopify.scripts.collection.update.ShopifyClient")
    )
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


def test_update_collection_dry_run_prints_input_and_skips_graphql(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "update.py",
                "--id",
                "gid://shopify/Collection/1",
                "--title",
                "Renamed",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert updatecmd.main() == 0
        assert client.graphql.call_count == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["id"] == "gid://shopify/Collection/1"
    assert parsed["title"] == "Renamed"


def test_update_collection_sends_only_provided_fields(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "collectionUpdate": {
                "collection": {
                    "id": "gid://shopify/Collection/1",
                    "title": "Renamed",
                    "handle": "renamed",
                },
                "userErrors": [],
            }
        }
        with patch.object(
            sys,
            "argv",
            [
                "update.py",
                "--id",
                "gid://shopify/Collection/1",
                "--title",
                "Renamed",
                "--output",
                "json",
            ],
        ):
            assert updatecmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables == {"input": {"id": "gid://shopify/Collection/1", "title": "Renamed"}}


def test_update_collection_userErrors_raises(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "collectionUpdate": {
                "collection": None,
                "userErrors": [{"field": ["title"], "message": "is too short"}],
            }
        }
        with (
            patch.object(
                sys,
                "argv",
                ["update.py", "--id", "gid://shopify/Collection/1", "--title", "x"],
            ),
            pytest.raises(ShopifyUserError),
        ):
            updatecmd.main()
