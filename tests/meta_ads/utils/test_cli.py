import argparse
import json

from meta_ads.utils import cli


def _parsed(argv):
    parser = argparse.ArgumentParser()
    cli.add_common_flags(parser)
    cli.add_meta_flags(parser)
    return parser.parse_args(argv)


def test_common_flag_defaults():
    args = _parsed([])
    assert args.output == "table"
    assert args.limit == 50
    assert args.config == "store-config.yaml"
    assert args.dry_run is False
    assert args.verbose is False


def test_meta_flags_api_version_and_yes():
    args = _parsed(["--api-version", "v19.0", "--yes"])
    assert args.api_version == "v19.0"
    assert args.yes is True


def test_meta_flag_defaults():
    args = _parsed([])
    assert args.api_version is None
    assert args.yes is False


def test_format_output_json():
    out = cli.format_output([{"id": "c1", "name": "Camp"}], "json")
    assert json.loads(out) == [{"id": "c1", "name": "Camp"}]


def test_format_output_table_renders_rows():
    out = cli.format_output([{"id": "c1", "name": "Camp"}], "table")
    assert "id" in out and "name" in out and "c1" in out


def test_format_output_empty_table():
    assert cli.format_output([], "table") == "(no rows)"
