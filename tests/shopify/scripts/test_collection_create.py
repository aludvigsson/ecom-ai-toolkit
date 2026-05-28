import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from shopify.scripts.collection import create as createcmd
from shopify.utils.client import ShopifyUserError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.collection.create.load_config"))
    mock_client_class = stack.enter_context(
        patch("shopify.scripts.collection.create.ShopifyClient")
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


def test_create_custom_collection_dry_run_prints_input_and_skips_graphql(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "create.py",
                "--title",
                "Summer",
                "--handle",
                "summer",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert createcmd.main() == 0
        assert client.graphql.call_count == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["title"] == "Summer"
    assert parsed["handle"] == "summer"
    assert "ruleSet" not in parsed


def test_create_smart_collection_reads_rules_from_file(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(
        json.dumps(
            {
                "appliedDisjunctively": False,
                "rules": [
                    {"column": "TAG", "relation": "EQUALS", "condition": "summer"},
                ],
            }
        )
    )
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "collectionCreate": {
                "collection": {
                    "id": "gid://shopify/Collection/1",
                    "title": "Summer",
                    "handle": "summer",
                },
                "userErrors": [],
            }
        }
        with patch.object(
            sys,
            "argv",
            [
                "create.py",
                "--title",
                "Summer",
                "--rules",
                str(rules_path),
                "--output",
                "json",
            ],
        ):
            assert createcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        inp = variables["input"]
        assert inp["title"] == "Summer"
        assert inp["ruleSet"] == {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "summer"},
            ],
        }


def test_create_userErrors_raises(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "collectionCreate": {
                "collection": None,
                "userErrors": [{"field": ["title"], "message": "is too short"}],
            }
        }
        with (
            patch.object(sys, "argv", ["create.py", "--title", "x"]),
            pytest.raises(ShopifyUserError),
        ):
            createcmd.main()
