from __future__ import annotations

import secrets
import string
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import ClickEvent, URLRecord
from .security import coarse_user_agent, normalize_target_url, safe_referrer_host


ALPHABET = string.ascii_letters + string.digits


class AliasConflict(ValueError):
    pass


class URLNotFound(LookupError):
    pass


class URLUnavailable(LookupError):
    pass


class URLShortenerService:
    def __init__(self, db: Session, base_url: str, alias_length: int = 7) -> None:
        self.db = db
        self.base_url = base_url.rstrip("/")
        self.alias_length = alias_length

    def create(
        self,
        target_url: str,
        custom_alias: str | None = None,
        expires_in_days: int | None = None,
    ) -> URLRecord:
        normalized = normalize_target_url(target_url)
        expires_at = (
            datetime.now(UTC) + timedelta(days=expires_in_days)
            if expires_in_days is not None
            else None
        )

        if custom_alias:
            return self._insert(custom_alias, normalized, expires_at, fail_on_conflict=True)

        for _ in range(5):
            code = "".join(secrets.choice(ALPHABET) for _ in range(self.alias_length))
            try:
                return self._insert(code, normalized, expires_at, fail_on_conflict=False)
            except AliasConflict:
                continue
        raise RuntimeError("Unable to allocate a unique short code after bounded retries")

    def _insert(
        self,
        code: str,
        target_url: str,
        expires_at: datetime | None,
        fail_on_conflict: bool,
    ) -> URLRecord:
        record = URLRecord(code=code, target_url=target_url, expires_at=expires_at)
        self.db.add(record)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            if fail_on_conflict:
                raise AliasConflict(f"Alias '{code}' is already in use") from exc
            raise AliasConflict(code) from exc
        self.db.refresh(record)
        return record

    def get(self, code: str) -> URLRecord:
        record = self.db.scalar(select(URLRecord).where(URLRecord.code == code))
        if record is None:
            raise URLNotFound(code)
        return record

    @staticmethod
    def _is_expired(record: URLRecord) -> bool:
        if record.expires_at is None:
            return False
        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at <= datetime.now(UTC)

    def resolve(self, code: str, referrer: str | None, user_agent: str | None) -> str:
        record = self.get(code)
        if record.disabled_at is not None or self._is_expired(record):
            raise URLUnavailable(code)

        event = ClickEvent(
            url_id=record.id,
            referrer_host=safe_referrer_host(referrer),
            user_agent_family=coarse_user_agent(user_agent),
        )
        self.db.add(event)
        self.db.commit()
        return record.target_url

    def disable(self, code: str) -> URLRecord:
        record = self.get(code)
        if record.disabled_at is None:
            record.disabled_at = datetime.now(UTC)
            self.db.commit()
            self.db.refresh(record)
        return record

    def analytics(self, code: str) -> dict[str, object]:
        record = self.get(code)
        total = self.db.scalar(
            select(func.count(ClickEvent.id)).where(ClickEvent.url_id == record.id)
        ) or 0

        date_expr = func.date(ClickEvent.clicked_at)
        daily_rows = self.db.execute(
            select(date_expr, func.count(ClickEvent.id))
            .where(ClickEvent.url_id == record.id)
            .group_by(date_expr)
            .order_by(date_expr)
        ).all()

        referrer_rows = self.db.execute(
            select(ClickEvent.referrer_host, func.count(ClickEvent.id).label("count"))
            .where(ClickEvent.url_id == record.id, ClickEvent.referrer_host.is_not(None))
            .group_by(ClickEvent.referrer_host)
            .order_by(func.count(ClickEvent.id).desc())
            .limit(5)
        ).all()

        return {
            "code": code,
            "total_clicks": int(total),
            "daily": [{"date": str(day), "clicks": count} for day, count in daily_rows],
            "top_referrers": [
                {"host": host, "clicks": count} for host, count in referrer_rows
            ],
        }

    def response_payload(self, record: URLRecord) -> dict[str, object]:
        return {
            "code": record.code,
            "target_url": record.target_url,
            "short_url": f"{self.base_url}/{record.code}",
            "created_at": record.created_at,
            "expires_at": record.expires_at,
            "disabled": record.disabled_at is not None,
        }
