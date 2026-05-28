import argparse

from shopify.utils.cli import add_common_flags, format_output


def test_add_common_flags_adds_all_expected():
    parser = argparse.ArgumentParser()
    add_common_flags(parser)
    ns = parser.parse_args(["--market", "se", "--dry-run", "--output", "json", "--limit", "10"])
    assert ns.market == "se"
    assert ns.dry_run is True
    assert ns.output == "json"
    assert ns.limit == 10


def test_format_output_json():
    out = format_output({"a": 1}, "json")
    assert '"a": 1' in out


def test_format_output_table_lists():
    out = format_output([{"id": 1, "name": "x"}, {"id": 2, "name": "y"}], "table")
    assert "id" in out and "name" in out
    assert "x" in out and "y" in out


def test_format_output_markdown_list():
    out = format_output([{"id": 1, "name": "x"}], "markdown")
    assert "| id" in out and "| name" in out
    assert "| 1" in out and "| x" in out


def test_format_output_table_empty_list():
    assert format_output([], "table") == "(no rows)"


def test_format_output_markdown_empty_list():
    assert format_output([], "markdown") == "_(no rows)_"
