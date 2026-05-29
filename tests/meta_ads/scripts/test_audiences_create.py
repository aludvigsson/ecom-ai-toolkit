import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.audiences import create as createcmd
from meta_ads.utils.client import MetaAPIError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.audiences.create.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.audiences.create.MetaClient"))
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_create_dry_run_prints_request_and_skips_post(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "create.py",
                "--account-id",
                "123",
                "--name",
                "VIP buyers",
                "--description",
                "Top spenders",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["path"] == "act_123/customaudiences"
    assert parsed["data"]["name"] == "VIP buyers"
    assert parsed["data"]["subtype"] == "CUSTOM"
    assert parsed["data"]["customer_file_source"] == "USER_PROVIDED_ONLY"


def test_create_posts_form_data(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "aud9"}
        with patch.object(
            sys,
            "argv",
            ["create.py", "--account-id", "123", "--name", "VIP buyers"],
        ):
            assert createcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "act_123/customaudiences"
        data = kwargs.get("data") or args[1]
        assert data["name"] == "VIP buyers"
        assert data["subtype"] == "CUSTOM"


def test_create_surfaces_api_error(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"error": {"message": "dup", "code": 2650, "fbtrace_id": "Z"}}
        with (
            patch.object(sys, "argv", ["create.py", "--account-id", "123", "--name", "X"]),
            pytest.raises(MetaAPIError),
        ):
            createcmd.main()
