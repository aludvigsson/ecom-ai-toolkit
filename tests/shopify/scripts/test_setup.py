"""Tests for shopify/scripts/setup.py — first-run interactive setup."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from shopify.scripts import setup as setup_mod


@pytest.fixture
def fake_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a fake project root with .env.example + store-config.example.yaml."""
    (tmp_path / ".env.example").write_text(
        "SHOPIFY_ADMIN_ACCESS_TOKEN=\nKLAVIYO_PRIVATE_API_KEY=\n",
        encoding="utf-8",
    )
    (tmp_path / "store-config.example.yaml").write_text(
        'store:\n  name: "Example"\n  shopify_domain: example.myshopify.com\n',
        encoding="utf-8",
    )
    # Pre-write a valid store-config.yaml so config loads cleanly.
    (tmp_path / "store-config.yaml").write_text(
        (
            "store:\n"
            '  name: "Test Shop"\n'
            "  primary_domain: test.com\n"
            "  shopify_domain: test-shop.myshopify.com\n"
            "  storefront_type: online_store_2\n"
            "  default_locale: en-US\n"
            "markets: []\n"
            "domains:\n"
            '  shopify: { enabled: true, api_version: "2025-10" }\n'
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_mod, "_project_root", lambda: tmp_path)
    return tmp_path


def test_setup_already_configured_returns_0(
    fake_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """If token exists and whoami succeeds, prints 'Already configured.' and exits 0."""
    (fake_project / ".env.local").write_text(
        "SHOPIFY_ADMIN_ACCESS_TOKEN=shpat_already_set_token_value_xxxxxxxxxx\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "shpat_already_set_token_value_xxxxxxxxxx")

    fake_shop = {
        "shop": {
            "name": "Test Shop",
            "primaryDomain": {"url": "https://test.com"},
            "plan": {"displayName": "Basic"},
        }
    }
    with patch("shopify.scripts.setup.ShopifyClient") as mock_client:
        mock_client.return_value.__enter__.return_value.graphql.return_value = fake_shop
        rc = setup_mod.main(["--auth-mode", "custom-app"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Already configured." in out
    assert "Test Shop" in out


def test_setup_custom_app_flow_writes_token_to_env_local(
    fake_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Custom-app paste flow: getpass returns a valid token, .env.local is updated."""
    (fake_project / ".env.local").write_text(
        "SHOPIFY_ADMIN_ACCESS_TOKEN=\nKLAVIYO_PRIVATE_API_KEY=existing\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("SHOPIFY_ADMIN_ACCESS_TOKEN", raising=False)
    pasted_token = "shpat_" + "x" * 40

    fake_shop = {
        "shop": {
            "name": "Test Shop",
            "primaryDomain": {"url": "https://test.com"},
            "plan": {"displayName": "Basic"},
        }
    }
    with (
        patch("shopify.scripts.setup.getpass.getpass", return_value=pasted_token),
        patch("shopify.scripts.setup.ShopifyClient") as mock_client,
    ):
        mock_client.return_value.__enter__.return_value.graphql.return_value = fake_shop
        rc = setup_mod.main(["--auth-mode", "custom-app"])

    assert rc == 0
    env_text = (fake_project / ".env.local").read_text(encoding="utf-8")
    assert f"SHOPIFY_ADMIN_ACCESS_TOKEN={pasted_token}" in env_text
    # Other lines preserved.
    assert "KLAVIYO_PRIVATE_API_KEY=existing" in env_text


def test_setup_cli_flow_reads_token_from_config_json(
    fake_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLI flow: shopify CLI runs, then we extract token from the config.json fixture."""
    (fake_project / ".env.local").write_text("SHOPIFY_ADMIN_ACCESS_TOKEN=\n", encoding="utf-8")
    monkeypatch.delenv("SHOPIFY_ADMIN_ACCESS_TOKEN", raising=False)

    cli_config = tmp_path / "cli-config.json"
    cli_token = "shpat_" + "c" * 40
    cli_config.write_text(
        json.dumps(
            {
                "7e9cb568abcd::test-shop": {
                    "myshopify.com": {
                        "currentUserId": "user-42",
                        "sessionsByUserId": {
                            "user-42": {
                                "accessToken": cli_token,
                                "expiresAt": "2026-05-29T12:00:00Z",
                                "scopes": ["read_products", "read_orders"],
                                "userEmail": "andreas@example.com",
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    fake_shop = {
        "shop": {
            "name": "Test Shop",
            "primaryDomain": {"url": "https://test.com"},
            "plan": {"displayName": "Basic"},
        }
    }
    with (
        patch("shopify.scripts.setup.shutil.which", return_value="/usr/local/bin/shopify"),
        patch("shopify.scripts.setup._find_cli_token_file", return_value=cli_config),
        patch("shopify.scripts.setup.subprocess.run") as mock_run,
        patch("shopify.scripts.setup.ShopifyClient") as mock_client,
    ):
        mock_client.return_value.__enter__.return_value.graphql.return_value = fake_shop
        rc = setup_mod.main(["--auth-mode", "cli"])

    assert rc == 0
    mock_run.assert_called_once()
    env_text = (fake_project / ".env.local").read_text(encoding="utf-8")
    assert f"SHOPIFY_ADMIN_ACCESS_TOKEN={cli_token}" in env_text


def test_setup_cli_flow_errors_when_shopify_not_on_path(
    fake_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """CLI mode without `shopify` on PATH should fail clearly."""
    (fake_project / ".env.local").write_text("SHOPIFY_ADMIN_ACCESS_TOKEN=\n", encoding="utf-8")
    monkeypatch.delenv("SHOPIFY_ADMIN_ACCESS_TOKEN", raising=False)

    with patch("shopify.scripts.setup.shutil.which", return_value=None):
        rc = setup_mod.main(["--auth-mode", "cli"])

    assert rc == 1
    err = capsys.readouterr().err
    assert "shopify" in err.lower()
    assert "PATH" in err or "custom-app" in err


def test_setup_invalid_token_format_rejected(
    fake_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Custom-app flow rejects bad tokens after 3 retries."""
    (fake_project / ".env.local").write_text("SHOPIFY_ADMIN_ACCESS_TOKEN=\n", encoding="utf-8")
    monkeypatch.delenv("SHOPIFY_ADMIN_ACCESS_TOKEN", raising=False)

    with patch("shopify.scripts.setup.getpass.getpass", return_value="not-a-real-token"):
        rc = setup_mod.main(["--auth-mode", "custom-app"])

    assert rc == 1
    err = capsys.readouterr().err
    assert "Invalid token" in err or "Failed to acquire" in err


def test_read_cli_token_for_store_handles_store_with_myshopify_suffix(
    tmp_path: Path,
) -> None:
    """`example-store.myshopify.com` should resolve to handle `example-store` in CLI config."""
    cli_config = tmp_path / "config.json"
    cli_config.write_text(
        json.dumps(
            {
                "7e9cb568abcd1234::example-store": {
                    "myshopify.com": {
                        "currentUserId": "user-1",
                        "sessionsByUserId": {
                            "user-1": {
                                "accessToken": "shpat_examplefixturetoken",
                                "expiresAt": "2026-05-29T12:00:00Z",
                                "scopes": ["read_products"],
                                "userEmail": "user@example.com",
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    result = setup_mod._read_cli_token_for_store(
        "example-store.myshopify.com", config_path=cli_config
    )
    assert result is not None
    token, metadata = result
    assert token == "shpat_examplefixturetoken"
    assert metadata["expires_at"] == "2026-05-29T12:00:00Z"
    assert metadata["scopes"] == ["read_products"]
    assert metadata["user_email"] == "user@example.com"


def test_read_cli_token_for_store_returns_none_when_store_missing(
    tmp_path: Path,
) -> None:
    """Lookup for an unknown store returns None."""
    cli_config = tmp_path / "config.json"
    cli_config.write_text(json.dumps({"abc::other-shop": {}}), encoding="utf-8")
    assert (
        setup_mod._read_cli_token_for_store("example-store.myshopify.com", config_path=cli_config)
        is None
    )


def test_write_token_to_env_local_preserves_other_keys(tmp_path: Path) -> None:
    """Token write replaces only the SHOPIFY_ADMIN_ACCESS_TOKEN line."""
    env_local = tmp_path / ".env.local"
    env_local.write_text(
        "SHOPIFY_ADMIN_ACCESS_TOKEN=old_value\n"
        "KLAVIYO_PRIVATE_API_KEY=kl_secret\n"
        "# A comment\n"
        "META_ACCESS_TOKEN=meta_secret\n",
        encoding="utf-8",
    )
    setup_mod._write_token_to_env_local("shpat_newvalue", env_local=env_local)
    text = env_local.read_text(encoding="utf-8")
    assert "SHOPIFY_ADMIN_ACCESS_TOKEN=shpat_newvalue" in text
    assert "old_value" not in text
    assert "KLAVIYO_PRIVATE_API_KEY=kl_secret" in text
    assert "META_ACCESS_TOKEN=meta_secret" in text
    assert "# A comment" in text


def test_write_token_to_env_local_appends_when_missing(tmp_path: Path) -> None:
    """If the token line doesn't exist, it's appended."""
    env_local = tmp_path / ".env.local"
    env_local.write_text("KLAVIYO_PRIVATE_API_KEY=kl\n", encoding="utf-8")
    setup_mod._write_token_to_env_local("shpat_newvalue", env_local=env_local)
    text = env_local.read_text(encoding="utf-8")
    assert "SHOPIFY_ADMIN_ACCESS_TOKEN=shpat_newvalue" in text
    assert "KLAVIYO_PRIVATE_API_KEY=kl" in text
