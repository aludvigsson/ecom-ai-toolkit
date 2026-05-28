from pathlib import Path

import pytest
from pydantic import ValidationError

from core.config import StoreConfig, load_config

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_valid_config_returns_storeconfig():
    cfg = load_config(FIXTURES / "valid_config.yaml")
    assert isinstance(cfg, StoreConfig)
    assert cfg.store.name == "Test Store"
    assert cfg.store.shopify_domain == "test-store.myshopify.com"


def test_market_lookup_by_code():
    cfg = load_config(FIXTURES / "valid_config.yaml")
    se = cfg.market("se")
    assert se.currency == "SEK"
    assert se.url_prefix == "/se"


def test_market_lookup_missing_raises():
    cfg = load_config(FIXTURES / "valid_config.yaml")
    with pytest.raises(KeyError):
        cfg.market("xx")


def test_domains_enabled():
    cfg = load_config(FIXTURES / "valid_config.yaml")
    assert cfg.domains["shopify"].enabled is True
    assert cfg.domains["klaviyo"].enabled is False


def test_load_missing_file_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.yaml")


def test_load_invalid_yaml_raises_validation(tmp_path):
    # invalid config: missing 'store' section
    with pytest.raises(ValidationError):
        load_config(FIXTURES / "invalid_no_store.yaml")
