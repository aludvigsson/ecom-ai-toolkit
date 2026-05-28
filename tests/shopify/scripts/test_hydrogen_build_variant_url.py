import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from core.config import StoreConfig
from shopify.scripts.hydrogen import build_variant_url


def _hydrogen_cfg() -> StoreConfig:
    return StoreConfig.model_validate(
        {
            "store": {
                "name": "Cura of Sweden",
                "primary_domain": "curaofsweden.com",
                "shopify_domain": "cura-of-sweden.myshopify.com",
                "storefront_type": "hydrogen",
                "default_locale": "sv-SE",
            },
            "markets": [
                {
                    "code": "se",
                    "name": "Sverige",
                    "locale": "sv-SE",
                    "currency": "SEK",
                    "url_prefix": "/se",
                },
                {
                    "code": "de",
                    "name": "Deutschland",
                    "locale": "de-DE",
                    "currency": "EUR",
                    "url_prefix": "/de",
                },
            ],
            "domains": {"shopify": {"enabled": True, "api_version": "2025-10"}},
        }
    )


def _os2_cfg() -> StoreConfig:
    return StoreConfig.model_validate(
        {
            "store": {
                "name": "Example",
                "primary_domain": "example.com",
                "shopify_domain": "example.myshopify.com",
                "storefront_type": "online_store_2",
                "default_locale": "en-US",
            },
            "markets": [
                {
                    "code": "us",
                    "name": "United States",
                    "locale": "en-US",
                    "currency": "USD",
                    "url_prefix": "",
                }
            ],
            "domains": {"shopify": {"enabled": True, "api_version": "2025-10"}},
        }
    )


def test_build_variant_url_by_id_for_se_market(capsys):
    with ExitStack() as stack:
        mock_cfg = stack.enter_context(
            patch("shopify.scripts.hydrogen.build_variant_url.load_config")
        )
        mock_cfg.return_value = _hydrogen_cfg()
        with patch.object(
            sys,
            "argv",
            [
                "build_variant_url.py",
                "--handle",
                "pearl-classic",
                "--variant-id",
                "12345",
                "--market",
                "se",
            ],
        ):
            assert build_variant_url.main() == 0
    out = capsys.readouterr().out.strip()
    assert out == "https://curaofsweden.com/se/products/pearl-classic?variant=12345"


def test_build_variant_url_by_sku_uses_sku_query_param(capsys):
    with ExitStack() as stack:
        mock_cfg = stack.enter_context(
            patch("shopify.scripts.hydrogen.build_variant_url.load_config")
        )
        mock_cfg.return_value = _hydrogen_cfg()
        with patch.object(
            sys,
            "argv",
            [
                "build_variant_url.py",
                "--handle",
                "pearl-classic",
                "--variant-sku",
                "ABC-001",
                "--market",
                "de",
            ],
        ):
            assert build_variant_url.main() == 0
    out = capsys.readouterr().out.strip()
    assert "?sku=ABC-001" in out
    assert "/de/products/pearl-classic" in out


def test_build_variant_url_default_market_falls_back_to_locale(capsys):
    with ExitStack() as stack:
        mock_cfg = stack.enter_context(
            patch("shopify.scripts.hydrogen.build_variant_url.load_config")
        )
        mock_cfg.return_value = _hydrogen_cfg()
        with patch.object(
            sys,
            "argv",
            [
                "build_variant_url.py",
                "--handle",
                "pearl-classic",
                "--variant-id",
                "999",
            ],
        ):
            assert build_variant_url.main() == 0
    out = capsys.readouterr().out.strip()
    assert out == "https://curaofsweden.com/se/products/pearl-classic?variant=999"


def test_build_variant_url_errors_on_online_store_2_storefront(capsys):
    with ExitStack() as stack:
        mock_cfg = stack.enter_context(
            patch("shopify.scripts.hydrogen.build_variant_url.load_config")
        )
        mock_cfg.return_value = _os2_cfg()
        with patch.object(
            sys,
            "argv",
            [
                "build_variant_url.py",
                "--handle",
                "pearl-classic",
                "--variant-id",
                "1",
                "--market",
                "us",
            ],
        ):
            assert build_variant_url.main() == 1
    captured = capsys.readouterr()
    assert "online_store_2" in captured.err
    assert "theme" in captured.err


def test_build_variant_url_strips_trailing_slash_from_primary_domain(capsys):
    cfg = _hydrogen_cfg()
    cfg.store.primary_domain = "curaofsweden.com/"
    with ExitStack() as stack:
        mock_cfg = stack.enter_context(
            patch("shopify.scripts.hydrogen.build_variant_url.load_config")
        )
        mock_cfg.return_value = cfg
        with patch.object(
            sys,
            "argv",
            [
                "build_variant_url.py",
                "--handle",
                "pearl-classic",
                "--variant-id",
                "12345",
                "--market",
                "se",
            ],
        ):
            assert build_variant_url.main() == 0
    out = capsys.readouterr().out.strip()
    assert "//se" not in out
    assert out == "https://curaofsweden.com/se/products/pearl-classic?variant=12345"


def test_build_variant_url_url_encodes_non_ascii_handle(capsys):
    with ExitStack() as stack:
        mock_cfg = stack.enter_context(
            patch("shopify.scripts.hydrogen.build_variant_url.load_config")
        )
        mock_cfg.return_value = _hydrogen_cfg()
        with patch.object(
            sys,
            "argv",
            [
                "build_variant_url.py",
                "--handle",
                "köpa-örngott",
                "--variant-id",
                "12345",
                "--market",
                "se",
            ],
        ):
            assert build_variant_url.main() == 0
    out = capsys.readouterr().out.strip()
    # ö encodes to %C3%B6
    assert "%C3%B6" in out
    assert "köpa" not in out


def test_build_variant_url_json_output(capsys):
    with ExitStack() as stack:
        mock_cfg = stack.enter_context(
            patch("shopify.scripts.hydrogen.build_variant_url.load_config")
        )
        mock_cfg.return_value = _hydrogen_cfg()
        with patch.object(
            sys,
            "argv",
            [
                "build_variant_url.py",
                "--handle",
                "pearl-classic",
                "--variant-id",
                "12345",
                "--market",
                "se",
                "--output",
                "json",
            ],
        ):
            assert build_variant_url.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["market"] == "se"
    assert parsed["handle"] == "pearl-classic"
    assert parsed["url"] == "https://curaofsweden.com/se/products/pearl-classic?variant=12345"
