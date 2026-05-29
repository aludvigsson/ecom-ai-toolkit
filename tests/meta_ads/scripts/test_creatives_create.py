import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.creatives import create as createcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.creatives.create.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.creatives.create.MetaClient"))
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


_SPEC = '{"page_id": "P1", "link_data": {"link": "https://example.com", "image_hash": "H1"}}'


def test_creative_create_dry_run_skips_post(monkeypatch, capsys):
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
                "Link Creative",
                "--object-story-spec",
                _SPEC,
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["path"] == "act_123/adcreatives"
    assert parsed["data"]["name"] == "Link Creative"
    assert parsed["data"]["object_story_spec"] == _SPEC


def test_creative_create_posts_spec(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "cr9"}
        with patch.object(
            sys,
            "argv",
            ["create.py", "--account-id", "123", "--name", "C", "--object-story-spec", _SPEC],
        ):
            assert createcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "act_123/adcreatives"
        assert (kwargs.get("data") or args[1])["object_story_spec"] == _SPEC


def test_creative_create_rejects_bad_spec_json(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with (
            patch.object(
                sys,
                "argv",
                ["create.py", "--account-id", "123", "--name", "C", "--object-story-spec", "{bad"],
            ),
            pytest.raises(SystemExit),
        ):
            createcmd.main()


def test_creative_create_requires_spec(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with (
            patch.object(sys, "argv", ["create.py", "--account-id", "123", "--name", "C"]),
            pytest.raises(SystemExit),
        ):
            createcmd.main()
