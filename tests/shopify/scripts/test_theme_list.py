import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from shopify.scripts.theme import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.theme.list.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.theme.list.ShopifyClient"))
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


def _theme_node(tid: str, name: str, role: str) -> dict:
    return {
        "node": {
            "id": f"gid://shopify/OnlineStoreTheme/{tid}",
            "name": name,
            "role": role,
            "processing": False,
            "previewable": True,
            "updatedAt": "2025-01-01T00:00:00Z",
        }
    }


def test_list_themes_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "themes": {
                "edges": [
                    _theme_node("1", "Dawn", "MAIN"),
                    _theme_node("2", "Backup", "UNPUBLISHED"),
                ]
            }
        }
        with patch.object(sys, "argv", ["list.py", "--output", "json"]):
            assert listcmd.main() == 0
        variables = _variables_from_call(client.graphql.call_args)
        assert variables == {"first": 50}
    out = capsys.readouterr().out
    parsed = json.loads(out)
    names = [t["name"] for t in parsed]
    assert "Dawn" in names
    assert "Backup" in names


def test_list_themes_filter_by_role(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "themes": {
                "edges": [
                    _theme_node("1", "Dawn", "MAIN"),
                    _theme_node("2", "Backup", "UNPUBLISHED"),
                    _theme_node("3", "Dev", "DEVELOPMENT"),
                ]
            }
        }
        with patch.object(sys, "argv", ["list.py", "--role", "MAIN", "--output", "json"]):
            assert listcmd.main() == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert len(parsed) == 1
    assert parsed[0]["name"] == "Dawn"
    assert parsed[0]["role"] == "MAIN"


def test_list_themes_no_role_filter_returns_all(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "themes": {
                "edges": [
                    _theme_node("1", "Dawn", "MAIN"),
                    _theme_node("2", "Backup", "UNPUBLISHED"),
                    _theme_node("3", "Dev", "DEVELOPMENT"),
                ]
            }
        }
        with patch.object(sys, "argv", ["list.py", "--output", "json"]):
            assert listcmd.main() == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert len(parsed) == 3
