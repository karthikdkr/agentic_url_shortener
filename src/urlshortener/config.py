from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/urlshortener.db")
    workflow_store_path: str = os.getenv("WORKFLOW_STORE_PATH", "./data/workflows.json")
    base_url: str = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
    rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
    rate_limit_window_seconds: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    alias_length: int = int(os.getenv("ALIAS_LENGTH", "7"))


settings = Settings()
