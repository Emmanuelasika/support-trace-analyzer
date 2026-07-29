<div align="center">

# TraceKit

**Turn a vague API failure into a safe, reproducible escalation.**

[![CI](https://github.com/Emmanuelasika/TraceKit/actions/workflows/ci.yml/badge.svg)](https://github.com/Emmanuelasika/TraceKit/actions/workflows/ci.yml)
[![Pages](https://github.com/Emmanuelasika/TraceKit/actions/workflows/pages.yml/badge.svg)](https://emmanuelasika.github.io/TraceKit/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-1.0.0-6f42c1.svg)](CHANGELOG.md)

</div>

TraceKit is a local-first incident-bundle CLI for developer support. It accepts
structured evidence, redacts secrets before output, classifies the failure
mode, and generates a Markdown artifact an engineering team can actually use.

**[Explore the interactive project site →](https://emmanuelasika.github.io/TraceKit/)**

> [!WARNING]
> This is a diagnostic aid, not a log archive. Do not use it as your production
> secret-management, observability, or customer-data system.

## Why this project

| Support problem | TraceKit behavior |
| --- | --- |
| “The API is broken” lacks actionable context | Produces a bounded classification, severity, evidence fingerprint, and next action. |
| Copying logs into tickets leaks secrets | Redacts known bearer, API-key, password, and `sk-…` forms before reports are written. |
| Escalations are inconsistent | Creates a repeatable incident-bundle contract and minimal reproduction guidance. |

## Quick start

```bash
git clone https://github.com/Emmanuelasika/TraceKit.git
cd tracekit
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m app.cli analyze fixtures/rate-limit.json --output reports/rate-limit.md
```

Or install the console command:

```bash
pip install -e .
tracekit validate fixtures/rate-limit.json
```

```text
Wrote safe incident bundle to reports/rate-limit.md
```

## Commands

| Command | Purpose |
| --- | --- |
| `tracekit redact <input>` | Inspect the safe version of a JSON evidence file. |
| `tracekit analyze <input> --output <report>` | Generate a sanitized investigation bundle. |
| `tracekit validate <input>` | Validate JSON/JSONL evidence without writing output. |
| `tracekit cluster <input>` | Count recurring failures using safe fingerprints. |

## Incident-bundle contract

```json
{
  "summary": "POST /v1/messages returned 429",
  "status_code": 429,
  "request_id": "req_123",
  "latency_ms": 214,
  "headers": {"retry-after": "2"},
  "body": "Authorization: Bearer [REDACTED]"
}
```

Reports contain only safe evidence, a stable fingerprint, a classification,
reproduction constraints, escalation criteria, and the next support action.

TraceKit accepts a single JSON object, an array of objects, or newline-delimited
JSON. See [the architecture note](docs/architecture.md) for its trust boundary
and fingerprint design.

## Quality gates

```bash
python -m compileall -q app
python -m pytest -q
docker build -t tracekit .
```

The GitHub Actions workflow executes the same checks on every push and pull
request. See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution standards and
[SECURITY.md](SECURITY.md) for the disclosure policy.

## Roadmap

- [ ] User-configurable, tested redaction policy packs
- [ ] SARIF/issue-template export with explicit human review
- [ ] Signed policy bundles for organization-specific severity rules

## License

Released under the [MIT License](LICENSE).
