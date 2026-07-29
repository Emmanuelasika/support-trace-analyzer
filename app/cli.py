"""Command-line interface for Support Trace Analyzer."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .core import EvidenceError, analyze_many, group_diagnoses, redact_value, render_markdown


def load_items(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise EvidenceError(f"input does not exist: {path}")
    if path.suffix.lower() == ".jsonl":
        items = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        parsed = json.loads(path.read_text(encoding="utf-8"))
        items = parsed if isinstance(parsed, list) else [parsed]
    if not items or not all(isinstance(item, dict) for item in items):
        raise EvidenceError("input must contain a JSON object, array of objects, or JSONL objects")
    return items


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tracekit", description="Create safe, reproducible incident bundles.")
    parser.add_argument("--version", action="version", version="Support Trace Analyzer 1.0.0")
    commands = parser.add_subparsers(dest="command", required=True)
    redact = commands.add_parser("redact", help="Print sanitized evidence without writing a report.")
    redact.add_argument("input", type=Path)
    validate = commands.add_parser("validate", help="Validate evidence against the input contract.")
    validate.add_argument("input", type=Path)
    analyze = commands.add_parser("analyze", help="Generate Markdown or JSON incident bundles.")
    analyze.add_argument("input", type=Path)
    analyze.add_argument("--output", type=Path, required=True)
    analyze.add_argument("--format", choices=("markdown", "json"), default="markdown")
    cluster = commands.add_parser("cluster", help="Group repeated evidence by safe fingerprint.")
    cluster.add_argument("input", type=Path)
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        items = load_items(args.input)
        if args.command == "redact":
            print(json.dumps(redact_value(items if len(items) > 1 else items[0]), indent=2, sort_keys=True))
            return 0
        diagnoses = analyze_many(items)
        if args.command == "validate":
            print(json.dumps({"valid": True, "items": len(diagnoses)}, sort_keys=True))
            return 0
        if args.command == "cluster":
            print(json.dumps({"groups": group_diagnoses(diagnoses)}, indent=2, sort_keys=True))
            return 0
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.format == "json":
            content = json.dumps([item.to_dict() for item in diagnoses], indent=2, sort_keys=True) + "\n"
        else:
            content = "\n\n---\n\n".join(render_markdown(item) for item in diagnoses)
        args.output.write_text(content, encoding="utf-8")
        print(f"Wrote {len(diagnoses)} safe incident bundle(s) to {args.output}")
        return 0
    except (EvidenceError, json.JSONDecodeError, OSError) as error:
        print(f"tracekit: {error}", file=sys.stderr)
        return 2


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
