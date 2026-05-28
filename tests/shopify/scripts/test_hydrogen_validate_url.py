import sys
from contextlib import ExitStack
from unittest.mock import patch

from shopify.scripts.hydrogen import validate_url


def test_validate_url_single_200(httpx_mock, capsys):
    httpx_mock.add_response(method="HEAD", url="https://example.test/ok", status_code=200)
    with ExitStack() as stack:
        mock_cfg = stack.enter_context(patch("shopify.scripts.hydrogen.validate_url.load_config"))
        mock_cfg.side_effect = FileNotFoundError
        with patch.object(
            sys,
            "argv",
            ["validate_url.py", "--url", "https://example.test/ok"],
        ):
            assert validate_url.main() == 0
    out = capsys.readouterr().out
    assert "200" in out
    assert "https://example.test/ok" in out


def test_validate_url_404_exits_nonzero(httpx_mock, capsys):
    httpx_mock.add_response(method="HEAD", url="https://example.test/missing", status_code=404)
    with ExitStack() as stack:
        mock_cfg = stack.enter_context(patch("shopify.scripts.hydrogen.validate_url.load_config"))
        mock_cfg.side_effect = FileNotFoundError
        with patch.object(
            sys,
            "argv",
            ["validate_url.py", "--url", "https://example.test/missing"],
        ):
            assert validate_url.main() == 1
    out = capsys.readouterr().out
    assert "404" in out


def test_validate_url_from_csv(httpx_mock, capsys, tmp_path):
    csv_path = tmp_path / "urls.csv"
    csv_path.write_text("url\nhttps://example.test/a\nhttps://example.test/b\n", encoding="utf-8")
    httpx_mock.add_response(method="HEAD", url="https://example.test/a", status_code=200)
    httpx_mock.add_response(method="HEAD", url="https://example.test/b", status_code=200)
    with ExitStack() as stack:
        mock_cfg = stack.enter_context(patch("shopify.scripts.hydrogen.validate_url.load_config"))
        mock_cfg.side_effect = FileNotFoundError
        with patch.object(
            sys,
            "argv",
            ["validate_url.py", "--from-csv", str(csv_path)],
        ):
            assert validate_url.main() == 0
    out = capsys.readouterr().out
    assert "https://example.test/a" in out
    assert "https://example.test/b" in out


def test_validate_url_no_follow_redirects_reports_3xx_as_failure(httpx_mock, capsys):
    httpx_mock.add_response(
        method="HEAD",
        url="https://example.test/start",
        status_code=301,
        headers={"Location": "https://example.test/final"},
    )
    with ExitStack() as stack:
        mock_cfg = stack.enter_context(patch("shopify.scripts.hydrogen.validate_url.load_config"))
        mock_cfg.side_effect = FileNotFoundError
        with patch.object(
            sys,
            "argv",
            [
                "validate_url.py",
                "--url",
                "https://example.test/start",
                "--no-follow-redirects",
                "--output",
                "json",
            ],
        ):
            assert validate_url.main() == 1
    out = capsys.readouterr().out
    import json as _json

    parsed = _json.loads(out)
    assert parsed[0]["status"] == 301
    assert parsed[0]["ok"] is False


def test_validate_url_follows_redirects_to_final_url(httpx_mock, capsys):
    httpx_mock.add_response(
        method="HEAD",
        url="https://example.test/start",
        status_code=301,
        headers={"Location": "https://example.test/final"},
    )
    httpx_mock.add_response(method="HEAD", url="https://example.test/final", status_code=200)
    with ExitStack() as stack:
        mock_cfg = stack.enter_context(patch("shopify.scripts.hydrogen.validate_url.load_config"))
        mock_cfg.side_effect = FileNotFoundError
        with patch.object(
            sys,
            "argv",
            ["validate_url.py", "--url", "https://example.test/start", "--output", "json"],
        ):
            assert validate_url.main() == 0
    out = capsys.readouterr().out
    import json as _json

    parsed = _json.loads(out)
    assert parsed[0]["final_url"] == "https://example.test/final"
    assert parsed[0]["status"] == 200
