import hashlib
import json

import pytest

from meta_ads.scripts.audiences import _users


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def test_normalize_lowercases_and_trims():
    assert _users.normalize("  Ada@B.COM  ") == "ada@b.com"


def test_hash_value_normalizes_then_sha256():
    assert _users.hash_value("  Ada@B.COM ") == _sha("ada@b.com")


def test_build_payload_email_schema():
    payload = _users.build_payload("EMAIL_SHA256", ["a@b.com", "c@d.com"])
    assert payload["schema"] == "EMAIL_SHA256"
    assert payload["data"] == [[_sha("a@b.com")], [_sha("c@d.com")]]


def test_build_payload_phone_schema():
    payload = _users.build_payload("PHONE_SHA256", ["+1 555 000"])
    # phone normalized to lowercase+trim only (digits left intact for the hash)
    assert payload["data"] == [[_sha("+1 555 000".strip().lower())]]


def test_payload_param_is_json_string():
    param = _users.payload_param("EMAIL_SHA256", ["a@b.com"])
    decoded = json.loads(param)
    assert decoded["schema"] == "EMAIL_SHA256"
    assert decoded["data"] == [[_sha("a@b.com")]]


def test_schema_for_resolves_email_and_phone():
    assert _users.schema_for("email") == "EMAIL_SHA256"
    assert _users.schema_for("phone") == "PHONE_SHA256"


def test_schema_for_rejects_unknown():
    with pytest.raises(ValueError):
        _users.schema_for("zip")


def test_load_identifiers_from_args_inline():
    args = type("A", (), {"value": ["a@b.com", "c@d.com"], "value_file": None})()
    assert _users.load_identifiers(args) == ["a@b.com", "c@d.com"]


def test_load_identifiers_from_file(tmp_path):
    f = tmp_path / "ids.txt"
    f.write_text("a@b.com\n\nc@d.com\n")
    args = type("A", (), {"value": None, "value_file": str(f)})()
    assert _users.load_identifiers(args) == ["a@b.com", "c@d.com"]


def test_load_identifiers_requires_some():
    args = type("A", (), {"value": None, "value_file": None})()
    with pytest.raises(ValueError):
        _users.load_identifiers(args)
