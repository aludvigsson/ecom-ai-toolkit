import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from shopify.scripts.theme import get_asset as getcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.theme.get_asset.load_config"))
    mock_client_class = stack.enter_context(patch("shopify.scripts.theme.get_asset.ShopifyClient"))
    mock_cfg.return_value.store.shopify_domain = "x.myshopify.com"
    mock_cfg.return_value.domains = {
        "shopify": type("D", (), {"api_version": "2025-10", "enabled": True})()
    }
    mock_client_instance = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, mock_client_instance


def _file_response(filename: str, content: str) -> dict:
    return {
        "theme": {
            "files": {
                "edges": [
                    {
                        "node": {
                            "filename": filename,
                            "body": {"content": content},
                            "size": len(content),
                            "contentType": "TEXT",
                        }
                    }
                ]
            }
        }
    }


def test_get_asset_text_output_prints_content(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = _file_response("sections/header.liquid", "hello liquid")
        with patch.object(
            sys,
            "argv",
            [
                "get_asset.py",
                "--theme-id",
                "gid://shopify/OnlineStoreTheme/1",
                "--filename",
                "sections/header.liquid",
            ],
        ):
            assert getcmd.main() == 0
    out = capsys.readouterr().out
    assert "hello liquid" in out


def test_get_asset_json_output_prints_node(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = _file_response("sections/header.liquid", "hello liquid")
        with patch.object(
            sys,
            "argv",
            [
                "get_asset.py",
                "--theme-id",
                "gid://shopify/OnlineStoreTheme/1",
                "--filename",
                "sections/header.liquid",
                "--output",
                "json",
            ],
        ):
            assert getcmd.main() == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["filename"] == "sections/header.liquid"
    assert parsed["body"]["content"] == "hello liquid"


def test_get_asset_missing_file_exits_2(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {"theme": {"files": {"edges": []}}}
        with patch.object(
            sys,
            "argv",
            [
                "get_asset.py",
                "--theme-id",
                "gid://shopify/OnlineStoreTheme/1",
                "--filename",
                "templates/missing.json",
            ],
        ):
            assert getcmd.main() == 2
    err = capsys.readouterr().err
    assert "templates/missing.json" in err
