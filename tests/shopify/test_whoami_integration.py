"""Integration test against a real Shopify dev shop.

Skipped unless SHOPIFY_INTEGRATION_TESTS=1 is set. Requires:
  - store-config.yaml pointing at a dev shop
  - SHOPIFY_ADMIN_ACCESS_TOKEN in .env.local
"""

from __future__ import annotations

import os

import pytest

from shopify.scripts import whoami

pytestmark = pytest.mark.skipif(
    os.environ.get("SHOPIFY_INTEGRATION_TESTS") != "1",
    reason="set SHOPIFY_INTEGRATION_TESTS=1 to run",
)


@pytest.mark.integration
def test_whoami_against_real_shop(capsys):
    rc = whoami.main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Shop:" in out
    assert "Domain:" in out
    assert "Plan:" in out
