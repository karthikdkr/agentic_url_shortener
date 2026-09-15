from __future__ import annotations

import pytest

from urlshortener.security import UnsafeURL, coarse_user_agent, normalize_target_url, safe_referrer_host


def test_rejects_non_http_scheme():
    with pytest.raises(UnsafeURL):
        normalize_target_url("javascript:alert(1)")


def test_rejects_embedded_credentials():
    with pytest.raises(UnsafeURL):
        normalize_target_url("https://user:password@example.com")


def test_analytics_helpers_reduce_data():
    assert safe_referrer_host("https://www.example.com/path?q=1") == "www.example.com"
    assert coarse_user_agent("Mozilla/5.0 Firefox/120") == "Firefox"
