# Architecture

TraceKit keeps analysis pure and filesystem access at the CLI boundary.

```text
JSON / JSONL evidence
        │
        ▼
contract validation ──► recursive redaction ──► deterministic diagnosis
                                                   │
                              ┌────────────────────┴───────────────────┐
                              ▼                                        ▼
                    Markdown / JSON bundle                    safe fingerprint groups
```

## Trust boundary

`app.core.redact_value` runs before any diagnosis is serialized. Reports never
receive the original evidence mapping. The fingerprint excludes request IDs and
timestamps so equivalent failures can cluster without treating correlation data
as identity.

## Failure behavior

Malformed contracts return exit code `2` with a bounded error. TraceKit performs
no network calls and does not silently upload or persist input evidence.
