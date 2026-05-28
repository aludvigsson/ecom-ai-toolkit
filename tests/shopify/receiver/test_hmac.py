import base64
import hashlib
import hmac as _hmac

from shopify.scripts.webhooks.receiver.hmac import verify_signature


def test_verify_signature_accepts_correct_signature():
    secret = "topsecret"
    body = b'{"id":1}'
    sig = base64.b64encode(_hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    assert verify_signature(secret=secret, body=body, header_value=sig) is True


def test_verify_signature_rejects_tampered_body():
    secret = "topsecret"
    body = b'{"id":1}'
    sig = base64.b64encode(_hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    assert verify_signature(secret=secret, body=b'{"id":2}', header_value=sig) is False


def test_verify_signature_rejects_missing_header():
    assert verify_signature(secret="x", body=b"y", header_value=None) is False
