import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.campaigns import create as createcmd
from meta_ads.utils.client import MetaAPIError


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.campaigns.create.load_config"))
    mock_client_class = stack.enter_context(patch("meta_ads.scripts.campaigns.create.MetaClient"))
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def _argv(*extra):
    return [
        "create.py",
        "--account-id",
        "123",
        "--name",
        "Spring Sale",
        "--objective",
        "OUTCOME_SALES",
        *extra,
    ]


def test_create_dry_run_forces_paused_and_skips_post(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(sys, "argv", _argv("--dry-run", "--output", "json")):
            assert createcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["path"] == "act_123/campaigns"
    assert parsed["data"]["status"] == "PAUSED"
    assert parsed["data"]["name"] == "Spring Sale"
    assert parsed["data"]["objective"] == "OUTCOME_SALES"


def test_create_posts_paused_body(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "c9"}
        with patch.object(sys, "argv", _argv()):
            assert createcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "act_123/campaigns"
        data = kwargs.get("data") or args[1]
        assert data["status"] == "PAUSED"
        assert data["name"] == "Spring Sale"
        assert data["objective"] == "OUTCOME_SALES"


def test_create_has_no_active_path(monkeypatch):
    """No flag may produce status=ACTIVE on create (safe-default guardrail)."""
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "c9"}
        # there is no --status/--active flag; argparse rejects an attempt to set one
        with (
            patch.object(sys, "argv", _argv("--status", "ACTIVE")),
            pytest.raises(SystemExit),
        ):
            createcmd.main()
        # and a clean create still pins PAUSED
        with patch.object(sys, "argv", _argv()):
            assert createcmd.main() == 0
        _, kwargs = client.post.call_args
        assert kwargs["data"]["status"] == "PAUSED"
        assert kwargs["data"]["status"] != "ACTIVE"


def test_create_serializes_special_ad_categories(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "c9"}
        with patch.object(sys, "argv", _argv("--special-ad-categories", "HOUSING")):
            assert createcmd.main() == 0
        _, kwargs = client.post.call_args
        assert kwargs["data"]["special_ad_categories"] == '["HOUSING"]'


def test_create_defaults_special_ad_categories_to_none_list(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "c9"}
        with patch.object(sys, "argv", _argv()):
            assert createcmd.main() == 0
        _, kwargs = client.post.call_args
        assert kwargs["data"]["special_ad_categories"] == "[]"


def test_create_surfaces_api_error(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {
            "error": {"message": "bad objective", "code": 100, "fbtrace_id": "Z"}
        }
        with (
            patch.object(sys, "argv", _argv()),
            pytest.raises(MetaAPIError),
        ):
            createcmd.main()
