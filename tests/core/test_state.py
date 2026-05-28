import json

import pytest

from core.state import StateSchemaError, load_state, load_state_v, save_state


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data = {"hello": "world", "n": 42, "items": [1, 2, 3]}
    save_state("shopify", "demo", data)
    loaded = load_state("shopify", "demo")
    # schema_version is now injected by save_state.
    assert loaded == {"schema_version": 1, **data}


def test_load_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert load_state("shopify", "never_saved") is None


def test_state_files_go_under_dot_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_state("klaviyo", "campaign_42", {"ok": True})
    assert (tmp_path / ".state" / "klaviyo" / "campaign_42.json").exists()


def test_save_is_atomic(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_state("shopify", "a", {"v": 1})
    # No tmp file should remain after a successful save.
    tmps = list((tmp_path / ".state" / "shopify").glob("*.tmp*"))
    assert tmps == []


def test_save_state_writes_schema_version(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_state("shopify", "demo", {"k": "v"})
    raw = json.loads((tmp_path / ".state" / "shopify" / "demo.json").read_text(encoding="utf-8"))
    assert raw["schema_version"] == 1
    assert raw["k"] == "v"


def test_load_state_v_returns_payload_when_version_matches(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_state("shopify", "demo", {"k": "v"})
    payload = load_state_v("shopify", "demo", expected_version=1)
    assert payload == {"schema_version": 1, "k": "v"}


def test_load_state_v_raises_on_version_mismatch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_state("shopify", "demo", {"k": "v"})  # schema_version=1
    with pytest.raises(StateSchemaError):
        load_state_v("shopify", "demo", expected_version=2)


def test_load_state_v_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert load_state_v("shopify", "never_saved", expected_version=1) is None


def test_save_state_accepts_custom_version(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_state("shopify", "demo", {"k": "v"}, schema_version=7)
    raw = json.loads((tmp_path / ".state" / "shopify" / "demo.json").read_text(encoding="utf-8"))
    assert raw["schema_version"] == 7
