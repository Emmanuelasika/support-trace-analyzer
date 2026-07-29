"""Typed incident analysis for TraceKit.

The module is deliberately pure: it performs validation, recursive redaction,
classification, deduplication fingerprints, and report generation without
network or filesystem access. That makes the safety boundary easy to test.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Iterable, Mapping

REDACTED = "[REDACTED]"
SECRET_KEYS = frozenset({"authorization", "api_key", "apikey", "password", "secret", "token", "access_token", "refresh_token"})
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"(?i)(Bearer\s+)[A-Za-z0-9._~+/-]+"),
    re.compile(r"(?i)((?:api[_-]?key|password|token|secret)\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
)


class EvidenceError(ValueError):
    """Raised when incident evidence violates the public input contract."""


@dataclass(frozen=True)
class Evidence:
    summary: str
    status_code: int | None = None
    request_id: str | None = None
    latency_ms: int | None = None
    attempts: int = 1
    occurred_at: str | None = None
    environment: str = "unknown"
    method: str | None = None
    url: str | None = None
    headers: Mapping[str, Any] = field(default_factory=dict)
    body: Any = None
    tags: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "Evidence":
        summary = raw.get("summary")
        if not isinstance(summary, str) or not 4 <= len(summary.strip()) <= 500:
            raise EvidenceError("summary must be a string between 4 and 500 characters")
        status = raw.get("status_code")
        if status is not None and (not isinstance(status, int) or not 100 <= status <= 599):
            raise EvidenceError("status_code must be an integer between 100 and 599")
        latency = raw.get("latency_ms")
        if latency is not None and (not isinstance(latency, int) or latency < 0):
            raise EvidenceError("latency_ms must be a non-negative integer")
        attempts = raw.get("attempts", 1)
        if not isinstance(attempts, int) or not 1 <= attempts <= 100:
            raise EvidenceError("attempts must be an integer between 1 and 100")
        headers = raw.get("headers", {})
        if not isinstance(headers, Mapping):
            raise EvidenceError("headers must be an object")
        tags = raw.get("tags", ())
        if not isinstance(tags, (list, tuple)) or not all(isinstance(tag, str) for tag in tags):
            raise EvidenceError("tags must be an array of strings")
        return cls(
            summary=summary.strip(), status_code=status, request_id=_optional_string(raw.get("request_id")),
            latency_ms=latency, attempts=attempts, occurred_at=_optional_string(raw.get("occurred_at")),
            environment=str(raw.get("environment", "unknown")), method=_optional_string(raw.get("method")),
            url=_optional_string(raw.get("url")), headers=headers, body=raw.get("body"), tags=tuple(tags),
        )


@dataclass(frozen=True)
class Diagnosis:
    fingerprint: str
    classification: str
    severity: str
    confidence: str
    title: str
    safe_evidence: Mapping[str, Any]
    observations: tuple[str, ...]
    next_actions: tuple[str, ...]
    reproduction: tuple[str, ...]
    escalation_criteria: tuple[str, ...]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise EvidenceError("optional text fields must be strings")
    return value[:2_000]


def redact_text(value: str) -> str:
    for pattern in SECRET_PATTERNS:
        value = pattern.sub(lambda match: (match.group(1) + REDACTED) if match.lastindex else REDACTED, value)
    return value


def redact_value(value: Any, *, key: str | None = None) -> Any:
    if key and key.lower().replace("-", "_") in SECRET_KEYS:
        return REDACTED
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return [redact_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(child_key): redact_value(item, key=str(child_key)) for child_key, item in value.items()}
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return redact_text(str(value))


def analyze(raw: Mapping[str, Any], *, clock: datetime | None = None) -> Diagnosis:
    evidence = Evidence.from_mapping(raw)
    safe = redact_value(asdict(evidence))
    status, summary = evidence.status_code, evidence.summary.lower()
    observations: list[str] = []
    if evidence.request_id:
        observations.append("A request/correlation ID is available for escalation.")
    else:
        observations.append("No request/correlation ID was supplied; capture one on the next attempt.")
    if evidence.latency_ms is not None:
        observations.append(f"Observed latency: {evidence.latency_ms} ms across {evidence.attempts} attempt(s).")

    if status in (401, 403) or any(word in summary for word in ("unauthorized", "forbidden", "authentication")):
        kind, severity, confidence, title = "authentication", "P1", "high", "Authentication or authorization failure"
        actions = ("Confirm the credential belongs to the intended environment and project.", "Verify scopes/roles without requesting the raw credential.", "Rotate the credential if exposure is suspected.")
    elif status == 429 or "rate limit" in summary:
        kind, severity, confidence, title = "rate_limit", "P2", "high", "Rate limit or concurrency pressure"
        actions = ("Honor Retry-After when present.", "Use bounded exponential backoff with jitter for retryable work.", "Measure concurrency and request volume before requesting a limit change.")
    elif status is not None and status >= 500:
        kind, severity, confidence, title = "transient_upstream", "P2", "high", "Upstream or transient server failure"
        actions = ("Retry idempotent work only with a bounded retry budget.", "Correlate request ID and UTC timestamps with provider status/telemetry.", "Preserve the sanitized minimal reproduction for escalation.")
    elif (evidence.latency_ms or 0) > 15_000 or "timeout" in summary:
        kind, severity, confidence, title = "latency", "P2", "medium", "Latency or timeout failure"
        actions = ("Measure p50/p95/p99 latency rather than relying on one sample.", "Reduce request size or expensive downstream work.", "Set an explicit timeout and cancellation budget.")
    elif status is not None and 400 <= status < 500:
        kind, severity, confidence, title = "request_contract", "P3", "high", "Request contract failure"
        actions = ("Validate required fields and types against the active API version.", "Remove optional fields until the minimal request succeeds.", "Record the sanitized error body and request ID.")
    else:
        kind, severity, confidence, title = "unknown", "P3", "low", "Unclassified integration failure"
        actions = ("Capture status code, request ID, UTC timestamp, and sanitized response body.", "Reduce the issue to the smallest deterministic reproduction.", "Compare one successful and one failed request.")

    if evidence.environment.lower() == "production" and severity == "P3":
        severity = "P2"
        observations.append("Production impact raised the minimum severity to P2.")
    normalized = {key: value for key, value in safe.items() if key not in {"request_id", "occurred_at"}}
    fingerprint = hashlib.sha256(json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
    reproduction = tuple(step for step in (
        f"Use {evidence.method or 'the original method'} against the sanitized endpoint shape.",
        "Replace credentials and customer content with synthetic values.",
        f"Reproduce with status expectation {status}." if status else "Capture the resulting status code.",
        "Record the UTC timestamp and request ID from the reproduction.",
    ))
    escalation = ("The failure remains reproducible after the recommended actions.", "Multiple customers or production workloads are affected.", "A security or data-integrity risk is suspected.")
    created_at = (clock or datetime.now(UTC)).isoformat()
    return Diagnosis(fingerprint, kind, severity, confidence, title, safe, tuple(observations), actions, reproduction, escalation, created_at)


def analyze_many(items: Iterable[Mapping[str, Any]], *, clock: datetime | None = None) -> list[Diagnosis]:
    return [analyze(item, clock=clock) for item in items]


def group_diagnoses(diagnoses: Iterable[Diagnosis]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for diagnosis in diagnoses:
        group = groups.setdefault(diagnosis.fingerprint, {"fingerprint": diagnosis.fingerprint, "classification": diagnosis.classification, "severity": diagnosis.severity, "count": 0})
        group["count"] += 1
    return sorted(groups.values(), key=lambda item: (-item["count"], item["fingerprint"]))


def render_markdown(result: Diagnosis) -> str:
    bullets = lambda values: "\n".join(f"- {value}" for value in values)
    safe = json.dumps(result.safe_evidence, indent=2, sort_keys=True)
    return f"""# Incident bundle `{result.fingerprint}`

> Generated {result.created_at}. Review before attaching to a real support case.

## Assessment

| Field | Value |
| --- | --- |
| Classification | `{result.classification}` |
| Severity | `{result.severity}` |
| Confidence | `{result.confidence}` |
| Summary | {result.title} |

## Observations

{bullets(result.observations)}

## Safe evidence

```json
{safe}
```

## Recommended actions

{bullets(result.next_actions)}

## Minimal reproduction

{bullets(result.reproduction)}

## Escalate when

{bullets(result.escalation_criteria)}
"""
