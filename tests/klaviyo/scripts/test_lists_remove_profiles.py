import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.lists import remove_profiles as rmcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.lists.remove_profiles.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.lists.remove_profiles.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_remove_dry_run_skips_call_without_yes(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["remove_profiles.py", "--id", "LST1", "--profile-id", "P1", "--dry-run"]
        ):
            assert rmcmd.main() == 0
        assert client.delete.call_count == 0


def test_remove_without_yes_errors(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["remove_profiles.py", "--id", "LST1", "--profile-id", "P1"]
        ):
            try:
                rc = rmcmd.main()
            except SystemExit as e:
                rc = e.code
        assert rc != 0
        assert client.delete.call_count == 0


def test_remove_with_yes_calls_delete_with_body(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.delete.return_value = {}
        with patch.object(
            sys, "argv", ["remove_profiles.py", "--id", "LST1", "--profile-id", "P1", "--yes"]
        ):
            assert rmcmd.main() == 0
        args, kwargs = client.delete.call_args
        assert args[0] == "lists/LST1/relationships/profiles"
        body = kwargs["json"]
        assert body["data"][0]["id"] == "P1"
