import argparse
import json

from klaviyo.utils import cli


def _parsed(argv):
    parser = argparse.ArgumentParser()
    cli.add_common_flags(parser)
    cli.add_klaviyo_flags(parser)
    return parser.parse_args(argv)


def test_common_flag_defaults():
    args = _parsed([])
    assert args.output == "table"
    assert args.limit == 50
    assert args.config == "store-config.yaml"
    assert args.dry_run is False
    assert args.verbose is False


def test_klaviyo_flags_revision_and_yes():
    args = _parsed(["--revision", "2099-01-01", "--yes"])
    assert args.revision == "2099-01-01"
    assert args.yes is True


def test_klaviyo_flag_defaults():
    args = _parsed([])
    assert args.revision is None
    assert args.yes is False


def test_format_output_json():
    out = cli.format_output([{"id": "p1", "email": "a@b.com"}], "json")
    assert json.loads(out) == [{"id": "p1", "email": "a@b.com"}]


def test_format_output_table_renders_rows():
    out = cli.format_output([{"id": "p1", "email": "a@b.com"}], "table")
    assert "id" in out and "email" in out and "p1" in out


def test_format_output_empty_table():
    assert cli.format_output([], "table") == "(no rows)"
