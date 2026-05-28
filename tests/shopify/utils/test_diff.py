from shopify.utils.diff import make_diff


def test_make_diff_returns_unified_diff_with_headers_and_changes():
    diff = make_diff("hello\nworld\n", "hello\nthere\n", path="greeting.txt")
    assert "--- a/greeting.txt" in diff
    assert "+++ b/greeting.txt" in diff
    assert "-world" in diff
    assert "+there" in diff


def test_make_diff_empty_when_identical():
    assert make_diff("abc", "abc") == ""


def test_make_diff_handles_added_lines():
    diff = make_diff("a\n", "a\nb\n")
    assert "+b" in diff


def test_make_diff_handles_removed_lines():
    diff = make_diff("a\nb\n", "a\n")
    assert "-b" in diff
