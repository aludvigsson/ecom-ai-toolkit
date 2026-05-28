"""Shopify HMAC SHA256 verification per
https://shopify.dev/docs/apps/webhooks/configuration/https#step-5-verify-the-webhook"""

from __future__ import annotations

import base64
import hashlib
import hmac


def verify_signature(*, secret: str, body: bytes, header_value: str | None) -> bool:
    if not header_value:
        return False
    expected = base64.b64encode(
        hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    ).decode("utf-8")
    return hmac.compare_digest(expected, header_value)
