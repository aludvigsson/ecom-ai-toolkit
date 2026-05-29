import hashlib
import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.audiences import remove_users as rmcmd


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.audiences.remove_users.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.audiences.remove_users.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_remove_users_dry_run_hashes_and_skips_delete(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "remove_users.py",
                "--id",
                "aud1",
                "--kind",
                "email",
                "--value",
                "A@B.com",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert rmcmd.main() == 0
        assert client.delete.call_count == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["method"] == "DELETE"
    assert parsed["path"] == "aud1/users"
    # payload rides as a query/form param, not a JSON body
    payload = json.loads(parsed["params"]["payload"])
    assert payload["schema"] == "EMAIL_SHA256"
    assert payload["data"] == [[_sha("a@b.com")]]
    assert "A@B.com" not in out


def test_remove_users_deletes_with_payload_param(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.delete.return_value = {"num_received": 1}
        with patch.object(
            sys,
            "argv",
            [
                "remove_users.py",
                "--id",
                "aud1",
                "--kind",
                "email",
                "--value",
                "a@b.com",
                "--yes",
            ],
        ):
            assert rmcmd.main() == 0
        args, kwargs = client.delete.call_args
        assert args[0] == "aud1/users"
        # must use params=, NOT a json/body kwarg
        assert "json" not in kwargs
        params = kwargs.get("params") or args[1]
        payload = json.loads(params["payload"])
        assert payload["data"] == [[_sha("a@b.com")]]


def test_remove_users_requires_yes_for_live(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with (
            patch.object(
                sys,
                "argv",
                [
                    "remove_users.py",
                    "--id",
                    "aud1",
                    "--kind",
                    "email",
                    "--value",
                    "a@b.com",
                ],
            ),
            pytest.raises(SystemExit),
        ):
            rmcmd.main()
        assert client.delete.call_count == 0
