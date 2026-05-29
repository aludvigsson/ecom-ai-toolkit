import hashlib
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.audiences import add_users as addcmd


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.audiences.add_users.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.audiences.add_users.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_add_users_dry_run_hashes_and_skips_post(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "add_users.py",
                "--id",
                "aud1",
                "--kind",
                "email",
                "--value",
                "Ada@B.com",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert addcmd.main() == 0
        assert client.post.call_count == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["method"] == "POST"
    assert parsed["path"] == "aud1/users"
    payload = json.loads(parsed["data"]["payload"])
    assert payload["schema"] == "EMAIL_SHA256"
    assert payload["data"] == [[_sha("ada@b.com")]]
    # raw identifier must not leak into the printed request
    assert "Ada@B.com" not in out


def test_add_users_posts_payload_form(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"num_received": 1, "num_invalid_entries": 0}
        with patch.object(
            sys,
            "argv",
            [
                "add_users.py",
                "--id",
                "aud1",
                "--kind",
                "email",
                "--value",
                "a@b.com",
                "--yes",
            ],
        ):
            assert addcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "aud1/users"
        data = kwargs.get("data") or args[1]
        payload = json.loads(data["payload"])
        assert payload["schema"] == "EMAIL_SHA256"
        assert payload["data"] == [[_sha("a@b.com")]]


def test_add_users_requires_yes_for_live(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with (
            patch.object(
                sys,
                "argv",
                ["add_users.py", "--id", "aud1", "--kind", "email", "--value", "a@b.com"],
            ),
            pytest.raises(SystemExit),
        ):
            addcmd.main()
        assert client.post.call_count == 0
