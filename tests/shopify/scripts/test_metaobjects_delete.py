import sys
from contextlib import ExitStack
from unittest.mock import patch

from shopify.scripts.metaobjects import delete as deletecmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.metaobjects.delete.load_config"))
    mock_client_class = stack.enter_context(
        patch("shopify.scripts.metaobjects.delete.ShopifyClient")
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


def test_delete_dry_run_does_not_require_yes_and_skips_graphql(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["delete.py", "--id", "gid://shopify/Metaobject/1", "--dry-run"],
        ):
            assert deletecmd.main() == 0
        assert client.graphql.call_count == 0
    out = capsys.readouterr().out
    assert "gid://shopify/Metaobject/1" in out


def test_delete_without_yes_errors(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["delete.py", "--id", "gid://shopify/Metaobject/1"],
        ):
            try:
                rc = deletecmd.main()
            except SystemExit as e:
                rc = e.code
        assert rc != 0
        assert client.graphql.call_count == 0


def test_delete_with_yes_calls_graphql_and_prints_id(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "metaobjectDelete": {
                "deletedId": "gid://shopify/Metaobject/1",
                "userErrors": [],
            }
        }
        with patch.object(
            sys,
            "argv",
            ["delete.py", "--id", "gid://shopify/Metaobject/1", "--yes"],
        ):
            assert deletecmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables == {"id": "gid://shopify/Metaobject/1"}
    out = capsys.readouterr().out
    assert "Deleted: gid://shopify/Metaobject/1" in out
