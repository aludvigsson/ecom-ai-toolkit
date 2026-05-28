from core.state import load_state, save_state


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data = {"hello": "world", "n": 42, "items": [1, 2, 3]}
    save_state("shopify", "demo", data)
    assert load_state("shopify", "demo") == data


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
