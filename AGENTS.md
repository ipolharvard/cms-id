# Repository Instructions

## Python

Use the repository virtual environment at `.venv` when it exists. Dependency
management uses `uv`; do not create an environment or change dependencies
without explicit approval.

Prefer:

```bash
make test
.venv/bin/pre-commit run --files <touched-files>
```

## CMS integration tests

Normal tests must not access the network. Tests marked `live_cms` download
official CMS materials and must only run when explicitly requested.

## Test style

Public deterministic behavior should be demonstrated with executable examples
in docstrings and the README. Use conventional pytest tests for HTTP, cache,
filesystem, concurrency, corrupt-input, and full parser integration behavior.

## Safety

Do not read secret-bearing files such as `.env`, `.env.*`, or `.envrc`.
Do not delete cached CMS materials or generated artifacts without approval.
