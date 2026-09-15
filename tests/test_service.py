from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from urlshortener.models import URLRecord
from urlshortener.service import AliasConflict, URLShortenerService, URLUnavailable


def test_create_custom_alias_and_resolve_records_click(db_session):
    service = URLShortenerService(db_session, "http://test")
    record = service.create("https://example.com/path", custom_alias="Example1")

    assert record.code == "Example1"
    assert service.resolve("Example1", "https://ref.example/a", "Mozilla Chrome/123") == "https://example.com/path"

    analytics = service.analytics("Example1")
    assert analytics["total_clicks"] == 1
    assert analytics["top_referrers"] == [{"host": "ref.example", "clicks": 1}]


def test_duplicate_custom_alias_is_conflict(db_session):
    service = URLShortenerService(db_session, "http://test")
    service.create("https://example.com", custom_alias="SameAlias")
    with pytest.raises(AliasConflict):
        service.create("https://example.org", custom_alias="SameAlias")


def test_expired_url_cannot_resolve(db_session):
    record = URLRecord(
        code="expired1",
        target_url="https://example.com",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    db_session.add(record)
    db_session.commit()
    service = URLShortenerService(db_session, "http://test")

    with pytest.raises(URLUnavailable):
        service.resolve("expired1", None, None)


def test_disable_is_idempotent(db_session):
    service = URLShortenerService(db_session, "http://test")
    service.create("https://example.com", custom_alias="disable1")
    first = service.disable("disable1")
    second = service.disable("disable1")
    assert first.disabled_at is not None
    assert second.disabled_at is not None
