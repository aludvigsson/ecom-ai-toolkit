import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from shopify.scripts.theme import update_asset as updatecmd
from shopify.utils.client import ShopifyUserError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.theme.update_asset.load_config"))
    mock_client_class = stack.enter_context(
        patch("shopify.scripts.theme.update_asset.ShopifyClient")
    )
    mock_cfg.return_value.store.shopify_domain = "x.myshopify.com"
    mock_cfg.return_value.domains = {
        "shopify": type("D", (), {"api_version": "2025-10", "enabled": True})()
    }
    mock_client_instance = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, mock_client_instance


def _fetch_response(content: str) -> dict:
    return {
        "theme": {
            "files": {
                "edges": [
                    {
                        "node": {
                            "filename": "sections/header.liquid",
                            "body": {"content": content},
                        }
                    }
                ]
            }
        }
    }


def _upsert_response(filename: str) -> dict:
    return {
        "themeFilesUpsert": {
            "upsertedThemeFiles": [{"filename": filename}],
            "userErrors": [],
        }
    }


def _variables_from_call(call_args):
    if len(call_args[0]) > 1:
        return call_args[0][1]
    return call_args[1].get("variables")


def test_update_asset_dry_run_prints_diff_and_skips_mutation(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = _fetch_response("old content")
        with patch.object(
            sys,
            "argv",
            [
                "update_asset.py",
                "--theme-id",
                "gid://shopify/OnlineStoreTheme/1",
                "--filename",
                "sections/header.liquid",
                "--content",
                "new content",
                "--dry-run",
            ],
        ):
            assert updatecmd.main() == 0
        # Only the fetch query — no upsert.
        assert client.graphql.call_count == 1
    err = capsys.readouterr().err
    assert "-old content" in err
    assert "+new content" in err


def test_update_asset_without_yes_errors(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = _fetch_response("old")
        with patch.object(
            sys,
            "argv",
            [
                "update_asset.py",
                "--theme-id",
                "gid://shopify/OnlineStoreTheme/1",
                "--filename",
                "sections/header.liquid",
                "--content",
                "new",
            ],
        ):
            rc = updatecmd.main()
        assert rc != 0
        # Only the fetch query — no upsert.
        assert client.graphql.call_count == 1
    err = capsys.readouterr().err
    assert "--yes" in err


def test_update_asset_with_yes_applies_upsert(monkeypatch, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            _fetch_response("old"),
            _upsert_response("sections/header.liquid"),
        ]
        with patch.object(
            sys,
            "argv",
            [
                "update_asset.py",
                "--theme-id",
                "gid://shopify/OnlineStoreTheme/1",
                "--filename",
                "sections/header.liquid",
                "--content",
                "new",
                "--yes",
            ],
        ):
            assert updatecmd.main() == 0
        assert client.graphql.call_count == 2
        upsert_vars = _variables_from_call(client.graphql.call_args_list[1])
        assert upsert_vars["themeId"] == "gid://shopify/OnlineStoreTheme/1"
        assert upsert_vars["files"] == [
            {
                "filename": "sections/header.liquid",
                "body": {"type": "TEXT", "value": "new"},
            }
        ]
    out = capsys.readouterr().out
    assert "Updated: sections/header.liquid" in out


def test_update_asset_from_file_reads_local_content(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    local = tmp_path / "header.liquid"
    local.write_text("from file content", encoding="utf-8")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            _fetch_response("old"),
            _upsert_response("sections/header.liquid"),
        ]
        with patch.object(
            sys,
            "argv",
            [
                "update_asset.py",
                "--theme-id",
                "gid://shopify/OnlineStoreTheme/1",
                "--filename",
                "sections/header.liquid",
                "--from-file",
                str(local),
                "--yes",
            ],
        ):
            assert updatecmd.main() == 0
        upsert_vars = _variables_from_call(client.graphql.call_args_list[1])
        assert upsert_vars["files"][0]["body"]["value"] == "from file content"


def test_update_asset_userErrors_raises(monkeypatch):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.side_effect = [
            _fetch_response("old"),
            {
                "themeFilesUpsert": {
                    "upsertedThemeFiles": [],
                    "userErrors": [
                        {
                            "field": ["files"],
                            "message": "Invalid file",
                            "code": "INVALID",
                        }
                    ],
                }
            },
        ]
        with (
            patch.object(
                sys,
                "argv",
                [
                    "update_asset.py",
                    "--theme-id",
                    "gid://shopify/OnlineStoreTheme/1",
                    "--filename",
                    "sections/header.liquid",
                    "--content",
                    "new",
                    "--yes",
                ],
            ),
            pytest.raises(ShopifyUserError),
        ):
            updatecmd.main()
