import pytest

from core.secrets import MissingSecretError, get_secret, require_secret


def test_get_secret_returns_value(monkeypatch):
    monkeypatch.setenv("FOO_TOKEN", "abc123")
    assert get_secret("FOO_TOKEN") == "abc123"


def test_get_secret_missing_returns_none(monkeypatch):
    monkeypatch.delenv("FOO_TOKEN", raising=False)
    assert get_secret("FOO_TOKEN") is None


def test_require_secret_present(monkeypatch):
    monkeypatch.setenv("BAR_KEY", "xyz")
    assert require_secret("BAR_KEY") == "xyz"


def test_require_secret_missing_raises_with_helpful_message(monkeypatch):
    monkeypatch.delenv("BAR_KEY", raising=False)
    with pytest.raises(MissingSecretError) as exc:
        require_secret("BAR_KEY")
    msg = str(exc.value)
    assert "BAR_KEY" in msg
    assert ".env.local" in msg


def test_load_env_local_populates_environ(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.local").write_text("LOADED_KEY=loaded_value\n")
    monkeypatch.delenv("LOADED_KEY", raising=False)
    from core.secrets import load_env_local

    load_env_local()
    import os

    assert os.environ.get("LOADED_KEY") == "loaded_value"


def test_get_secret_auto_loads_env_local_from_cwd(tmp_path, monkeypatch):
    """Auto-load works from any cwd, every test, regardless of prior loads."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AUTO_LOADED_KEY", raising=False)
    (tmp_path / ".env.local").write_text("AUTO_LOADED_KEY=auto_value\n")
    assert get_secret("AUTO_LOADED_KEY") == "auto_value"
