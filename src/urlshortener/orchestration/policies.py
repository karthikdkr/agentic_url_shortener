from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PolicyFinding:
    severity: str
    code: str
    message: str


_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)(api[_ ]?key|secret|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
)

_DANGEROUS_PATTERNS = (
    re.compile(r"(?i)\bDROP\s+TABLE\b"),
    re.compile(r"(?i)\beval\s*\("),
    re.compile(r"(?i)verify\s*=\s*False"),
)


def inspect_artifact(artifact: Any) -> list[PolicyFinding]:
    text = str(artifact)
    findings: list[PolicyFinding] = []
    for pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(
                PolicyFinding("critical", "secret_exposure", "Potential secret material detected")
            )
    for pattern in _DANGEROUS_PATTERNS:
        if pattern.search(text):
            findings.append(
                PolicyFinding("high", "unsafe_construct", "Potentially unsafe construct detected")
            )
    return findings


def critical(findings: list[PolicyFinding]) -> bool:
    return any(item.severity == "critical" for item in findings)
