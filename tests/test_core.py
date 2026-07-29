import json
from datetime import UTC, datetime

import pytest

from app.cli import run
from app.core import EvidenceError, analyze, group_diagnoses, redact_value, render_markdown

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_recursive_redaction_covers_keys_tokens_and_email():
    safe = redact_value({"authorization": "Bearer secret", "nested": {"body": "api_key=abc123 user@example.com"}})
    assert safe["authorization"] == "[REDACTED]"
    assert "abc123" not in str(safe)
    assert "user@example.com" not in str(safe)


def test_rate_limit_report_contains_actionable_sections_without_secret():
    result = analyze({"summary": "rate limit", "status_code": 429, "body": "Bearer sk_not_for_tickets_123456"}, clock=NOW)
    report = render_markdown(result)
    assert result.classification == "rate_limit"
    assert "Retry-After" in report
    assert "sk_not_for_tickets" not in report


def test_production_raises_unknown_failure_to_p2():
    result = analyze({"summary": "unclear failure", "environment": "production"}, clock=NOW)
    assert result.severity == "P2"


def test_server_error_has_bounded_retry_guidance():
    result = analyze({"summary": "upstream failed", "status_code": 503, "request_id": "req_42"}, clock=NOW)
    assert result.classification == "transient_upstream"
    assert "idempotent" in " ".join(result.next_actions)


def test_invalid_contract_is_rejected():
    with pytest.raises(EvidenceError, match="status_code"):
        analyze({"summary": "bad status", "status_code": 700}, clock=NOW)


def test_fingerprint_ignores_request_id_and_timestamp():
    first = analyze({"summary": "same failure", "status_code": 500, "request_id": "req_1", "occurred_at": "one"}, clock=NOW)
    second = analyze({"summary": "same failure", "status_code": 500, "request_id": "req_2", "occurred_at": "two"}, clock=NOW)
    assert first.fingerprint == second.fingerprint


def test_grouping_counts_repeated_safe_failure():
    items = [analyze({"summary": "same failure", "status_code": 500, "request_id": f"req_{i}"}, clock=NOW) for i in range(3)]
    assert group_diagnoses(items)[0]["count"] == 3


def test_cli_generates_json_bundle(tmp_path):
    source, output = tmp_path / "input.json", tmp_path / "report.json"
    source.write_text(json.dumps({"summary": "forbidden", "status_code": 403, "headers": {"authorization": "secret"}}))
    assert run(["analyze", str(source), "--output", str(output), "--format", "json"]) == 0
    content = output.read_text()
    assert '"classification": "authentication"' in content
    assert "secret" not in content
