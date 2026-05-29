import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.profiles import subscribe as subcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.profiles.subscribe.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.profiles.subscribe.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_subscribe_dry_run_builds_job_body(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "subscribe.py",
                "--email",
                "a@b.com",
                "--list-id",
                "LST1",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert subcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["data"]["type"] == "profile-subscription-bulk-create-job"
    assert parsed["data"]["relationships"]["list"]["data"]["id"] == "LST1"
    profile = parsed["data"]["attributes"]["profiles"]["data"][0]
    assert profile["attributes"]["email"] == "a@b.com"


def test_subscribe_posts_to_job_endpoint(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {}
        with patch.object(sys, "argv", ["subscribe.py", "--email", "a@b.com", "--list-id", "LST1"]):
            assert subcmd.main() == 0
        args, _ = client.post.call_args
        assert args[0] == "profile-subscription-bulk-create-jobs"
