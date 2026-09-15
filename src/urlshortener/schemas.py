from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class CreateURLRequest(BaseModel):
    url: HttpUrl
    custom_alias: str | None = Field(default=None, min_length=4, max_length=32)
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)

    @field_validator("custom_alias")
    @classmethod
    def validate_alias(cls, value: str | None) -> str | None:
        if value is None:
            return None
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
        if any(char not in allowed for char in value):
            raise ValueError("custom_alias may contain only letters, digits, and underscore")
        return value


class URLResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    target_url: str
    short_url: str
    created_at: datetime
    expires_at: datetime | None
    disabled: bool


class DailyClickCount(BaseModel):
    date: str
    clicks: int


class AnalyticsResponse(BaseModel):
    code: str
    total_clicks: int
    daily: list[DailyClickCount]
    top_referrers: list[dict[str, Any]]


class EngineeringRunRequest(BaseModel):
    requirement: str = Field(min_length=10, max_length=10000)
    scenario_type: Literal["greenfield", "brownfield", "ambiguous"] = "greenfield"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalRequest(BaseModel):
    approved: bool
    reviewer: str = Field(min_length=1, max_length=120)
    note: str = Field(default="", max_length=2000)
    payload: dict[str, Any] = Field(default_factory=dict)


class ReplanRequest(BaseModel):
    changed_requirement: str = Field(min_length=10, max_length=10000)
    reason: str = Field(min_length=3, max_length=1000)
