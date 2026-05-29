import json
import sys
from contextlib import ExitStack
from unittest.mock import patch

from klaviyo.scripts.templates import list as listcmd


def _setup_mocks(stack):
    mock_cfg = stack.enter_context(patch("klaviyo.scripts.templates.list.load_config"))
    mock_client_class = stack.enter_context(patch("klaviyo.scripts.templates.list.KlaviyoClient"))
    mock_cfg.return_value.domains = {
        "klaviyo": type("D", (), {"api_version": "2024-10-15", "enabled": True})()
    }
    client = mock_client_class.return_value.__enter__.return_value
    return mock_cfg, mock_client_class, client


def test_templates_list_emits_json(monkeypatch, capsys):
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_examplefixturekey")
    with ExitStack() as stack:
        _, _, client = _setup_mocks(stack)
        client.paginate.return_value = iter(
            [{"id": "TPL1", "type": "template", "attributes": {"name": "Welcome"}}]
        )
        with patch.object(sys, "argv", ["list.py", "--output", "json"]):
            assert listcmd.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["id"] == "TPL1"
    assert parsed[0]["name"] == "Welcome"
