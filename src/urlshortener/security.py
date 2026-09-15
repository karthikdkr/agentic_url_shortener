from __future__ import annotations

from urllib.parse import urlparse


class UnsafeURL(ValueError):
    pass


def normalize_target_url(raw: str) -> str:
    value = raw.strip()
    if len(value) > 2048:
        raise UnsafeURL("URL exceeds 2048 characters")

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURL("Only http and https URLs are allowed")
    if not parsed.netloc:
        raise UnsafeURL("URL must contain a host")
    if parsed.username or parsed.password:
        raise UnsafeURL("Embedded credentials are not allowed")
    return value


def safe_referrer_host(referrer: str | None) -> str | None:
    if not referrer:
        return None
    try:
        host = urlparse(referrer).hostname
    except ValueError:
        return None
    return host[:255] if host else None


def coarse_user_agent(user_agent: str | None) -> str | None:
    if not user_agent:
        return None
    value = user_agent.lower()
    families = (
        ("edg/", "Edge"),
        ("chrome/", "Chrome"),
        ("firefox/", "Firefox"),
        ("safari/", "Safari"),
        ("curl/", "curl"),
        ("python", "Python"),
    )
    for marker, label in families:
        if marker in value:
            return label
    return "Other"
