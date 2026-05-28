import sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

from shopify.scripts.translations import register as regcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("shopify.scripts.translations.register.load_config"))
    mock_client_class = stack.enter_context(
        patch("shopify.scripts.translations.register.ShopifyClient")
    )
    mock_cfg.return_value.store.shopify_domain = "x.myshopify.com"
    mock_cfg.return_value.domains = {
        "shopify": type("D", (), {"api_version": "2025-10", "enabled": True})()
    }
    mock_client_instance = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, mock_client_instance


def _write_csv(path: Path, rows: list[dict]) -> None:
    headers = list(rows[0].keys())
    lines = [",".join(headers)]
    for r in rows:
        lines.append(",".join(str(r.get(h, "")) for h in headers))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _variables_from_call(call_args):
    if len(call_args[0]) > 1:
        return call_args[0][1]
    return call_args[1].get("variables")


def test_register_dry_run_prints_groups_and_skips_graphql(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    csv_path = tmp_path / "tx.csv"
    _write_csv(
        csv_path,
        [
            {
                "resource_id": "gid://shopify/Product/1",
                "locale": "sv-SE",
                "key": "title",
                "value": "Hej",
                "translatable_content_digest": "d1",
            },
            {
                "resource_id": "gid://shopify/Product/1",
                "locale": "sv-SE",
                "key": "body_html",
                "value": "Kropp",
                "translatable_content_digest": "d2",
            },
            {
                "resource_id": "gid://shopify/Product/2",
                "locale": "sv-SE",
                "key": "title",
                "value": "Hej2",
                "translatable_content_digest": "d3",
            },
        ],
    )
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["register.py", "--from-csv", str(csv_path), "--dry-run"],
        ):
            assert regcmd.main() == 0
        assert client.graphql.call_count == 0
    out = capsys.readouterr().out
    assert "gid://shopify/Product/1" in out
    assert "gid://shopify/Product/2" in out
    assert "2 translations" in out
    assert "1 translations" in out


def test_register_groups_by_resource_id(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    csv_path = tmp_path / "tx.csv"
    _write_csv(
        csv_path,
        [
            {
                "resource_id": "gid://shopify/Product/1",
                "locale": "sv-SE",
                "key": "title",
                "value": "Hej",
                "translatable_content_digest": "d1",
            },
            {
                "resource_id": "gid://shopify/Product/1",
                "locale": "sv-SE",
                "key": "body_html",
                "value": "Kropp",
                "translatable_content_digest": "d2",
            },
            {
                "resource_id": "gid://shopify/Product/2",
                "locale": "sv-SE",
                "key": "title",
                "value": "Hej2",
                "translatable_content_digest": "d3",
            },
        ],
    )
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.graphql.return_value = {
            "translationsRegister": {
                "translations": [],
                "userErrors": [],
            }
        }
        with patch.object(sys, "argv", ["register.py", "--from-csv", str(csv_path)]):
            assert regcmd.main() == 0
        assert client.graphql.call_count == 2

        calls_by_resource = {}
        for call in client.graphql.call_args_list:
            variables = _variables_from_call(call)
            calls_by_resource[variables["resourceId"]] = variables["translations"]

        assert "gid://shopify/Product/1" in calls_by_resource
        assert "gid://shopify/Product/2" in calls_by_resource

        p1 = calls_by_resource["gid://shopify/Product/1"]
        assert len(p1) == 2
        keys = sorted(t["key"] for t in p1)
        assert keys == ["body_html", "title"]
        for t in p1:
            assert t["locale"] == "sv-SE"
            assert "translatableContentDigest" in t
            assert "value" in t

        p2 = calls_by_resource["gid://shopify/Product/2"]
        assert len(p2) == 1
        assert p2[0]["key"] == "title"
        assert p2[0]["translatableContentDigest"] == "d3"


def test_register_rejects_csv_missing_digest_column(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_x")
    csv_path = tmp_path / "tx.csv"
    _write_csv(
        csv_path,
        [
            {
                "resource_id": "gid://shopify/Product/1",
                "locale": "sv-SE",
                "key": "title",
                "value": "Hej",
                "translatable_content_digest": "",
            },
        ],
    )
    with ExitStack() as stack:
        _setup_mocks(stack)
        with (
            patch.object(sys, "argv", ["register.py", "--from-csv", str(csv_path)]),
            pytest.raises((RuntimeError, ValueError)) as exc_info,
        ):
            regcmd.main()
        assert "translatable_content_digest" in str(exc_info.value)
