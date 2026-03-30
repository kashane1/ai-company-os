#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python3}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

mkdir -p "$ROOT/build/test-results" "$ROOT/build/coverage"

args=(
  "$PYTHON_BIN" -m pytest
  tests/python
  --junitxml="$ROOT/build/test-results/python-junit.xml"
  --cov=apps
  --cov=packages
  --cov-report=term-missing
  --cov-report=xml:"$ROOT/build/coverage/python-coverage.xml"
)

if [[ -n "${PYTHON_COVERAGE_MIN:-}" ]]; then
  args+=(--cov-fail-under "${PYTHON_COVERAGE_MIN}")
fi

"${args[@]}"
