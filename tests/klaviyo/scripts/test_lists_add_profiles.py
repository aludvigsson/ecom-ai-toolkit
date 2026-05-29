import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.lists import add_profiles as addcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.lists.add_profiles.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.lists.add_profiles.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_add_profiles_dry_run_builds_relationship_body(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "add_profiles.py",
                "--id",
                "LST1",
                "--profile-id",
                "P1",
                "--profile-id",
                "P2",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert addcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    ids = [d["id"] for d in parsed["data"]]
    assert ids == ["P1", "P2"]
    assert parsed["data"][0]["type"] == "profile"


def test_add_profiles_posts_to_relationships(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {}
        with patch.object(sys, "argv", ["add_profiles.py", "--id", "LST1", "--profile-id", "P1"]):
            assert addcmd.main() == 0
        args, _ = client.post.call_args
        assert args[0] == "lists/LST1/relationships/profiles"
