import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.profiles import unsubscribe as unsubcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.profiles.unsubscribe.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.profiles.unsubscribe.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_unsubscribe_dry_run_skips_post_without_yes(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "unsubscribe.py",
                "--email",
                "a@b.com",
                "--list-id",
                "LST1",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert unsubcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "profile-subscription-bulk-delete-job"


def test_unsubscribe_without_yes_errors_in_live_mode(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["unsubscribe.py", "--email", "a@b.com", "--list-id", "LST1"]
        ):
            try:
                rc = unsubcmd.main()
            except SystemExit as e:
                rc = e.code
        assert rc != 0
        assert client.post.call_count == 0


def test_unsubscribe_with_yes_posts(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {}
        with patch.object(
            sys, "argv", ["unsubscribe.py", "--email", "a@b.com", "--list-id", "LST1", "--yes"]
        ):
            assert unsubcmd.main() == 0
        args, _ = client.post.call_args
        assert args[0] == "profile-subscription-bulk-delete-jobs"
