<div align="center">

# Support Trace Analyzer

**I built Support Trace Analyzer to turn messy API evidence into a support escalation I would be comfortable sending to engineering.**

[![CI](https://github.com/Emmanuelasika/support-trace-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/Emmanuelasika/support-trace-analyzer/actions/workflows/ci.yml)
[![Pages](https://github.com/Emmanuelasika/support-trace-analyzer/actions/workflows/pages.yml/badge.svg)](https://emmanuelasika.github.io/support-trace-analyzer/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MIT license](https://img.shields.io/badge/license-MIT-151515.svg)](LICENSE)

[Walk through the rate-limit investigation](https://emmanuelasika.github.io/support-trace-analyzer/) · [Read the architecture note](docs/architecture.md) · [Report a bug](https://github.com/Emmanuelasika/support-trace-analyzer/issues)

</div>

---

An engineer cannot investigate “requests sometimes fail.” They need a status,
a request ID, a timestamp, the size of the blast radius, and a reproduction.
The support engineer collecting those details also has to avoid pasting a
customer credential into Jira or Slack.

Support Trace Analyzer is the small, local CLI I wanted at that boundary. It accepts one
incident or a batch, checks that the evidence is structurally useful, redacts
secret- and identity-shaped values, assigns an explainable diagnosis, and
writes a reviewable Markdown or JSON bundle.

It does **not** call an LLM, upload a log, query a provider, or pretend that a
heuristic is a root-cause analysis.

## See it work in 60 seconds

```bash
git clone https://github.com/Emmanuelasika/support-trace-analyzer.git
cd support-trace-analyzer
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e .

tracekit validate fixtures/rate-limit.json
tracekit analyze fixtures/rate-limit.json --output reports/rate-limit.md
```

> The product and repository are named **Support Trace Analyzer**. The installed
> command remains `tracekit` for compatibility with existing scripts and the
> Python console entry point.

Actual command output:

```text
{"items": 1, "valid": true}
Wrote 1 safe incident bundle(s) to reports/rate-limit.md
```

The fixture deliberately contains this unsafe value:

```json
{
  "summary": "POST /v1/messages returned 429",
  "status_code": 429,
  "request_id": "req_demo_123",
  "latency_ms": 214,
  "headers": {"retry-after": "2"},
  "body": "Authorization: Bearer sk_demo_secret_123456789"
}
```

The report contains the useful context, but the body becomes:

```json
{
  "body": "Authorization: Bearer [REDACTED]",
  "headers": {"retry-after": "2"},
  "request_id": "req_demo_123",
  "status_code": 429
}
```

It also records:

```text
Classification  rate_limit
Severity        P2
Confidence      high
Fingerprint     7b4755b5ccd192b9
Next action     Honor Retry-After when present.
```

The complete generated artifact is checked in at
[`reports/demo.md`](reports/demo.md). Review is intentional: the first line of
every report tells the operator to inspect it before attaching it to a case.

## Where this earns its keep

| Situation | What I would run | What I get |
| --- | --- | --- |
| A customer pasted a raw request into chat | `tracekit redact case.json` | A sanitized view I can safely inspect before sharing |
| A 429 complaint needs engineering review | `tracekit analyze case.json --output case.md` | Classification, evidence, next actions, reproduction and escalation threshold |
| A hand-written intake may be malformed | `tracekit validate case.json` | A non-zero exit and a bounded error before a bad ticket is created |
| Twenty failures might be the same incident | `tracekit cluster failures.jsonl` | Counts grouped by a privacy-conscious failure fingerprint |
| Another system needs structured output | `tracekit analyze case.json --output result.json --format json` | The full diagnosis as machine-readable JSON |

Support Trace Analyzer is especially useful in developer support, API onboarding, incident
intake, and escalation-quality reviews. It can also sit in a shell script before
a report is attached to a ticket. It is less useful when the real job is
searching terabytes of telemetry or correlating distributed traces; use an
observability platform for that.

## Case study: the retry storm that looked like provider downtime

This is a synthetic case, but the workflow is based on a common support pattern.

### 09:17 — the report arrives

A customer says the messaging API is “down in production.” Their sample has a
`429`, a two-second `Retry-After` header, a request ID, 214 ms latency, and a
Bearer credential in the copied body.

At this point there are three risks:

1. the secret travels further than it should;
2. the word “down” sends the case to an upstream-availability queue;
3. a retry loop magnifies the rate limit while people investigate.

### 09:20 — support makes the evidence safe

```bash
tracekit redact customer-sample.json > safe-sample.json
tracekit validate customer-sample.json
```

Redaction is recursive. Secret-shaped keys such as `authorization`, `api_key`,
`password` and `token` are replaced, as are Bearer tokens, `sk-…` values and
email addresses embedded inside strings.

### 09:23 — the bundle narrows the first response

```bash
tracekit analyze customer-sample.json --output escalation.md
```

The deterministic rule sees `429` and produces `rate_limit / P2 / high`. It
does not claim to know *why* the limit was reached. It suggests the reversible
checks supported by the evidence: honor `Retry-After`, add bounded exponential
backoff with jitter, and measure concurrency before asking for a limit change.

### 09:31 — a batch reveals repetition

The operator exports sanitized JSONL-shaped incidents and runs:

```bash
tracekit cluster morning-failures.jsonl
```

```json
{
  "groups": [
    {
      "classification": "rate_limit",
      "count": 3,
      "fingerprint": "7b4755b5ccd192b9",
      "severity": "P2"
    }
  ]
}
```

`request_id` and `occurred_at` are deliberately excluded from the fingerprint,
so repeated instances can land together. The remaining sanitized evidence is
included, so materially different requests do not collapse merely because both
returned 429.

### The useful outcome

Engineering receives one reviewed artifact, not three screenshots. The
credential is absent, the suspected failure family is explicit, and the report
states when the case should escalate. If reducing concurrency resolves the
issue, support can close it without an availability investigation. If it
persists, the request ID and reproduction steps are ready.

## The four commands

### `redact` — inspect before sharing

```bash
tracekit redact evidence.json
```

Prints sanitized JSON to stdout. This is useful for piping into another local
tool. Support Trace Analyzer never edits the source file.

### `validate` — fail early

```bash
tracekit validate evidence.jsonl
```

Accepts a JSON object, a JSON array of objects, or newline-delimited JSON.
Validation rejects impossible status codes, negative latency, invalid headers,
more than 100 attempts, and summaries outside the 4–500 character contract.
Input/contract failures exit with code `2`, which makes the command scriptable.

### `analyze` — build the handoff

```bash
tracekit analyze evidence.json --output incident.md
tracekit analyze evidence.json --output incident.json --format json
```

Markdown is intended for a human-reviewed escalation. JSON is intended for
local automation. A batch produces one diagnosis per item.

### `cluster` — spot recurring shapes

```bash
tracekit cluster incidents.jsonl
```

Returns groups sorted by count. The fingerprint is a grouping aid—not a global
incident ID and not proof of a shared root cause.

## What happens between input and report

```text
 JSON / JSONL
      │
      ▼
 shape + field validation
      │  reject invalid evidence (exit 2)
      ▼
 recursive redaction  ◀── trust boundary
      │
      ├── safe evidence ──► SHA-256 fingerprint (first 16 hex chars)
      │
      ▼
 deterministic classification
      │
      ├── auth: 401 / 403
      ├── rate limit: 429
      ├── upstream: 5xx
      ├── latency: >15s or timeout wording
      ├── request contract: other 4xx
      └── unknown
      ▼
 reviewed Markdown / JSON bundle
```

The analysis module is deliberately pure: no network and no filesystem access.
The CLI owns file reading and writing. Redaction occurs before evidence is put
into a `Diagnosis`, so output renderers only receive the sanitized form. See
[`docs/architecture.md`](docs/architecture.md) for the exact trust boundary.

## Severity and confidence are intentionally boring

| Evidence | Result |
| --- | --- |
| `401`, `403`, or authentication wording | `authentication`, P1, high |
| `429` or “rate limit” | `rate_limit`, P2, high |
| `5xx` | `transient_upstream`, P2, high |
| latency above 15 seconds or timeout wording | `latency`, P2, medium |
| another `4xx` | `request_contract`, P3, high |
| insufficient evidence | `unknown`, P3, low |

An unknown production failure is raised from P3 to P2. This is triage policy,
not an SLA and not a substitute for your organization’s incident matrix.

## Input contract

Only `summary` is required:

```json
{
  "summary": "Checkout request timed out",
  "status_code": 504,
  "request_id": "req_01J...",
  "latency_ms": 30112,
  "attempts": 3,
  "occurred_at": "2026-07-29T09:17:00Z",
  "environment": "production",
  "method": "POST",
  "url": "https://api.example.test/v1/checkout",
  "headers": {"content-type": "application/json"},
  "body": {"error": "gateway timeout"},
  "tags": ["checkout", "enterprise"]
}
```

Unknown fields are ignored by the current dataclass constructor. Optional text
fields are capped at 2,000 characters; this is a guardrail, not a complete file
size limit.

## Honest limitations

- Redaction is pattern-based. An unusual credential format can evade it, and an
  innocent string that looks like a secret can be removed. Always review output.
- Email addresses are redacted, but Support Trace Analyzer is not a comprehensive PII/DLP
  engine. Names, phone numbers and arbitrary customer payloads are not detected.
- Classification is a first-routing heuristic. It does not inspect live service
  health, SDK versions, account limits, traces, or provider-side telemetry.
- Fingerprints exclude request IDs and timestamps but include other safe fields.
  Tiny evidence changes can produce a different group; similar evidence can
  still have different root causes.
- Generated timestamps make reports non-byte-identical across runs.
- Support Trace Analyzer has no ticket-system integration by design. A human decides what
  leaves the machine.

These are the next areas I would tackle for a production rollout: configurable
and tested policy packs, schema versioning, explicit file-size ceilings, and a
preview/approval step before any ticket integration.

## Development

```bash
pip install -e ".[dev]"
python -m ruff check .
python -m compileall -q app
python -m pytest -q
docker build -t tracekit .
```

The GitHub workflow runs lint, compilation, tests, the installed CLI smoke test,
and a containerized fixture analysis on Python 3.11 and 3.12 where applicable.
Contributions are welcome; start with [`CONTRIBUTING.md`](CONTRIBUTING.md).
Please report security issues using [`SECURITY.md`](SECURITY.md), not a public
issue.

## Why I built it this way

Good product support is not just being helpful in a reply. It is evidence
quality, safe handling, correct routing, and knowing where certainty ends.
Support Trace Analyzer is deliberately small enough that a support engineer can read the
classification and redaction rules, challenge them, and improve them.

— Emmanuel Asika

Released under the [MIT License](LICENSE).
