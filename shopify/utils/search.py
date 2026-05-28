"""Shopify search-syntax helpers.

Shopify's `query:` argument on resource lists uses a small DSL where values
can be single-quoted to allow spaces/special chars. To embed a literal
single quote or backslash, the value must be backslash-escaped.

See: https://shopify.dev/docs/api/usage/search-syntax
"""

from __future__ import annotations


def escape_search_value(value: str) -> str:
    r"""Escape a value for use inside `field:'<value>'` Shopify search strings.

    Replaces `\` with `\\` first (must be done first), then `'` with `\'`.
    """
    return value.replace("\\", "\\\\").replace("'", "\\'")
