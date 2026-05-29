import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.segments import get as getcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.segments.get.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.segments.get.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_get_segment_by_id(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "data": {"id": "SEG1", "type": "segment", "attributes": {"name": "Engaged"}}
        }
        with patch.object(sys, "argv", ["get.py", "--id", "SEG1", "--output", "json"]):
            assert getcmd.main() == 0
        client.get.assert_called_once_with("segments/SEG1")
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "SEG1"
    assert parsed["name"] == "Engaged"


def test_get_segment_with_members(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.get.return_value = {
            "data": {"id": "SEG1", "type": "segment", "attributes": {"name": "Engaged"}}
        }
        client.paginate.return_value = iter(
            [{"id": "01H", "type": "profile", "attributes": {"email": "a@b.com"}}]
        )
        with patch.object(
            sys, "argv", ["get.py", "--id", "SEG1", "--with-members", "--output", "json"]
        ):
            assert getcmd.main() == 0
        client.paginate.assert_called_once()
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["members"][0]["email"] == "a@b.com"
