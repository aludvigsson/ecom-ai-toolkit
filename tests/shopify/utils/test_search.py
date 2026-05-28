from shopify.utils.search import escape_search_value


def test_escapes_single_quote():
    assert escape_search_value("O'Brien") == r"O\'Brien"


def test_escapes_backslash_first_then_quote():
    # Order matters: a literal backslash must not become an escape for the
    # subsequent quote escape.
    assert escape_search_value(r"a\b'c") == r"a\\b\'c"


def test_passes_through_plain_text():
    assert escape_search_value("plain text") == "plain text"


def test_handles_empty_string():
    assert escape_search_value("") == ""
