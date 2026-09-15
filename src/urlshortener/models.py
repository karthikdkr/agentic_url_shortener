from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class URLRecord(Base):
    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    clicks: Mapped[list["ClickEvent"]] = relationship(
        back_populates="url",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ClickEvent(Base):
    __tablename__ = "click_events"
    __table_args__ = (
        Index("ix_click_events_url_clicked", "url_id", "clicked_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url_id: Mapped[int] = mapped_column(ForeignKey("urls.id", ondelete="CASCADE"), nullable=False)
    clicked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    referrer_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_agent_family: Mapped[str | None] = mapped_column(String(80), nullable=True)

    url: Mapped[URLRecord] = relationship(back_populates="clicks")
