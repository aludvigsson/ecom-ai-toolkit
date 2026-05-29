import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.campaigns import schedule as schedcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.campaigns.schedule.load_config"))
    mock_client_class = stack.enter_context(
        patch("klaviyo.scripts.campaigns.schedule.KlaviyoClient")
    )
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_schedule_dry_run_prints_body_without_yes(monkeypatch, capsys):
    # Per Task 4 note: scheduling lives on the campaign (send_strategy.datetime),
    # then a campaign-send-job is POSTed. dry-run prints both planned operations.
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            [
                "schedule.py",
                "--id",
                "CMP1",
                "--at",
                "2026-06-01T09:00:00",
                "--dry-run",
                "--output",
                "json",
            ],
        ):
            assert schedcmd.main() == 0
        assert client.post.call_count == 0
        assert client.patch.call_count == 0
    parsed = json.loads(capsys.readouterr().out)
    # The campaign PATCH carries the schedule via send_strategy.
    campaign = parsed["campaign"]["data"]
    assert campaign["type"] == "campaign"
    assert campaign["id"] == "CMP1"
    assert campaign["attributes"]["send_strategy"]["method"] == "static"
    assert campaign["attributes"]["send_strategy"]["datetime"] == "2026-06-01T09:00:00"
    # The send job triggers the (scheduled) send and carries just type + id.
    send_job = parsed["send_job"]["data"]
    assert send_job["type"] == "campaign-send-job"
    assert send_job["id"] == "CMP1"


def test_schedule_without_yes_errors_in_live_mode(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys, "argv", ["schedule.py", "--id", "CMP1", "--at", "2026-06-01T09:00:00"]
        ):
            try:
                rc = schedcmd.main()
            except SystemExit as e:
                rc = e.code
        assert rc != 0
        assert client.post.call_count == 0
        assert client.patch.call_count == 0


def test_schedule_with_yes_patches_campaign_then_posts_send_job(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.patch.return_value = {"data": {"id": "CMP1", "type": "campaign"}}
        client.post.return_value = {"data": {"id": "CMP1", "type": "campaign-send-job"}}
        with patch.object(
            sys, "argv", ["schedule.py", "--id", "CMP1", "--at", "2026-06-01T09:00:00", "--yes"]
        ):
            assert schedcmd.main() == 0
        # Schedule is set on the campaign first.
        patch_args, patch_kwargs = client.patch.call_args
        assert patch_args[0] == "campaigns/CMP1"
        patch_body = patch_kwargs.get("json") or patch_args[1]
        strategy = patch_body["data"]["attributes"]["send_strategy"]
        assert strategy["method"] == "static"
        assert strategy["datetime"] == "2026-06-01T09:00:00"
        # Then the send job is triggered.
        post_args, post_kwargs = client.post.call_args
        assert post_args[0] == "campaign-send-jobs"
        post_body = post_kwargs.get("json") or post_args[1]
        assert post_body["data"]["type"] == "campaign-send-job"
        assert post_body["data"]["id"] == "CMP1"


def test_schedule_send_now_omits_send_strategy(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        with patch.object(
            sys,
            "argv",
            ["schedule.py", "--id", "CMP1", "--send-now", "--dry-run", "--output", "json"],
        ):
            assert schedcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    # Send-now does not set a schedule on the campaign; no campaign PATCH planned.
    assert parsed["campaign"] is None
    send_job = parsed["send_job"]["data"]
    assert send_job["type"] == "campaign-send-job"
    assert send_job["id"] == "CMP1"
    assert "scheduled_at" not in send_job.get("attributes", {})
