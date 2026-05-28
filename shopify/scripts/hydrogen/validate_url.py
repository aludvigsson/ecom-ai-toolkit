"""Validate Hydrogen URLs via HEAD requests.

For each input URL, issues a HEAD request and reports the final status.
Follows redirects; reports the final URL after the redirect chain.

Exits non-zero if any URL returns status >= 400.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse
import contextlib

import httpx

from core.config import load_config
from core.http import HttpClient
from core.logging import get_logger
from shopify.utils.cli import add_common_flags, configure_logging_from_args, format_output
from shopify.utils.csv_io import read_csv_dicts

_log = get_logger("ecom.shopify.hydrogen.validate_url")


def _check_one(http: HttpClient, url: str) -> dict:
    try:
        response = http.head(url, follow_redirects=True)
        status = response.status_code
        final = str(response.url)
        return {"url": url, "status": status, "final_url": final, "ok": status < 400}
    except httpx.HTTPStatusError as exc:
        response = exc.response
        status = response.status_code
        final = str(response.url)
        return {"url": url, "status": status, "final_url": final, "ok": False}
    except httpx.HTTPError as exc:
        return {
            "url": url,
            "status": 0,
            "final_url": "",
            "ok": False,
            "error": str(exc),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HEAD-check Hydrogen URLs.")
    add_common_flags(parser)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", action="append", help="URL to check (repeatable)")
    group.add_argument(
        "--from-csv",
        dest="from_csv",
        help="CSV path with a 'url' column",
    )
    args = parser.parse_args(argv)
    configure_logging_from_args(args)

    # store-config is optional here; load it for logging context if present.
    with contextlib.suppress(FileNotFoundError):
        load_config(args.config)

    urls: list[str] = []
    if args.url:
        urls.extend(args.url)
    elif args.from_csv:
        for row in read_csv_dicts(args.from_csv):
            url = (row.get("url") or "").strip()
            if url:
                urls.append(url)

    if not urls:
        print("Error: no URLs provided", file=sys.stderr)
        return 2

    results: list[dict] = []
    any_failed = False
    # validators check current state; retries hide problems
    with HttpClient(timeout=15.0, max_retries=0) as http:
        for url in urls:
            row = _check_one(http, url)
            results.append(row)
            if not row["ok"]:
                any_failed = True

    print(format_output(results, args.output))
    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
