from shopify.utils.csv_io import read_csv_dicts


def test_read_csv_dicts(tmp_path):
    p = tmp_path / "data.csv"
    p.write_text("sku,price\nABC,99.00\nDEF,49.50\n")
    rows = list(read_csv_dicts(p))
    assert rows == [{"sku": "ABC", "price": "99.00"}, {"sku": "DEF", "price": "49.50"}]


def test_read_csv_dicts_accepts_string_path(tmp_path):
    p = tmp_path / "data.csv"
    p.write_text("a,b\n1,2\n")
    rows = list(read_csv_dicts(str(p)))
    assert rows == [{"a": "1", "b": "2"}]
