# Contributing

## Local checks

Run `python -m compileall -q app` and `python -m pytest -q` before opening a
pull request. Add a regression test for every behavior change.

## Data safety

Never commit credentials, raw customer payloads, or production request logs.
Fixtures must be synthetic and should exercise redaction behavior.

## Pull requests

Keep changes focused, document user-visible behavior, and explain any changes
to redaction or severity logic in the PR description.
