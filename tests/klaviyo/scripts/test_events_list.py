import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.events import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.events.list.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.events.list.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_events_list_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [
                {
                    "id": "EVT1",
                    "type": "event",
                    "attributes": {
                        "datetime": "2026-01-02T03:04:05Z",
                        "event_properties": {"x": 1},
                    },
                }
            ]
        )
        with patch.object(sys, "argv", ["list.py", "--output", "json"]):
            assert listcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "EVT1"
    assert parsed[0]["datetime"] == "2026-01-02T03:04:05Z"


def test_events_list_metric_filter_builds_param(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(sys, "argv", ["list.py", "--metric-id", "MET1"]):
            assert listcmd.main() == 0
        _, kwargs = client.paginate.call_args
        assert kwargs["params"]["filter"] == 'equals(metric_id,"MET1")'


def test_events_list_combines_filters(monkeypatch):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter([])
        with patch.object(
            sys, "argv", ["list.py", "--profile-id", "P1", "--since", "2026-01-01T00:00:00Z"]
        ):
            assert listcmd.main() == 0
        _, kwargs = client.paginate.call_args
        assert kwargs["params"]["filter"] == (
            'and(equals(profile_id,"P1"),greater-or-equal(datetime,2026-01-01T00:00:00Z))'
        )
