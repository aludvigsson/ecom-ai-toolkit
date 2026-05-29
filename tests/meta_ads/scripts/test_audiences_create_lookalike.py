import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from meta_ads.scripts.audiences import create_lookalike as lookcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("meta_ads.scripts.audiences.create_lookalike.load_config"))
    mock_client_class = stack.enter_context(
        patch("meta_ads.scripts.audiences.create_lookalike.MetaClient")
    )
    mock_cfg.return_value.domains = {
        "meta_ads": type("D", (), {"api_version": "v21.0", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_lookalike_dry_run_builds_spec(monkeypatch, capsys):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "create_lookalike.py",
                "--account-id",
                "123",
                "--name",
                "LAL 1% US",
                "--source-audience-id",
                "aud1",
                "--country",
                "US",
                "--ratio",
                "0.01",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert lookcmd.main() == 0
        assert client.post.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["path"] == "act_123/customaudiences"
    assert parsed["data"]["subtype"] == "LOOKALIKE"
    assert parsed["data"]["origin_audience_id"] == "aud1"
    spec = json.loads(parsed["data"]["lookalike_spec"])
    assert spec["country"] == "US"
    assert spec["ratio"] == 0.01


def test_lookalike_posts_form_data(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.post.return_value = {"id": "lal9"}
        with patch.object(
            sys,
            "argv",
            [
                "create_lookalike.py",
                "--account-id",
                "123",
                "--name",
                "LAL",
                "--source-audience-id",
                "aud1",
                "--country",
                "US",
                "--ratio",
                "0.03",
            ],
        ):
            assert lookcmd.main() == 0
        args, kwargs = client.post.call_args
        assert args[0] == "act_123/customaudiences"
        data = kwargs.get("data") or args[1]
        assert data["subtype"] == "LOOKALIKE"
        spec = json.loads(data["lookalike_spec"])
        assert spec["ratio"] == 0.03


def test_lookalike_ratio_out_of_range_errors(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "EAAexampletoken")
    with ExitStack() as stack:
        _setup_mocks(stack)
        with (
            patch.object(
                sys,
                "argv",
                [
                    "create_lookalike.py",
                    "--account-id",
                    "123",
                    "--name",
                    "LAL",
                    "--source-audience-id",
                    "aud1",
                    "--country",
                    "US",
                    "--ratio",
                    "0.5",
                ],
            ),
            pytest.raises(SystemExit),
        ):
            lookcmd.main()
