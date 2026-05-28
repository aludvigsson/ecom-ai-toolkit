import argparse
import logging

from shopify.utils.cli import add_common_flags, configure_logging_from_args, format_output


def test_add_common_flags_adds_all_expected():
    parser = argparse.ArgumentParser()
    add_common_flags(parser)
    ns = parser.parse_args(["--dry-run", "--output", "json", "--limit", "10", "--verbose"])
    assert ns.dry_run is True
    assert ns.output == "json"
    assert ns.limit == 10
    assert ns.verbose is True


def test_add_common_flags_no_longer_registers_market():
    parser = argparse.ArgumentParser()
    add_common_flags(parser)
    # --market was removed; argparse should reject it.
    import pytest

    with pytest.raises(SystemExit):
        parser.parse_args(["--market", "se"])


def test_configure_logging_from_args_sets_debug_when_verbose():
    parser = argparse.ArgumentParser()
    add_common_flags(parser)
    ns = parser.parse_args(["--verbose"])
    # Reset to a known state so the test is deterministic.
    logging.getLogger("ecom").setLevel(logging.WARNING)
    configure_logging_from_args(ns)
    assert logging.getLogger("ecom").level == logging.DEBUG


def test_configure_logging_from_args_noop_without_verbose():
    parser = argparse.ArgumentParser()
    add_common_flags(parser)
    ns = parser.parse_args([])
    logging.getLogger("ecom").setLevel(logging.WARNING)
    configure_logging_from_args(ns)
    assert logging.getLogger("ecom").level == logging.WARNING


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
