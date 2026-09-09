#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -n "${PYTHON_BIN:-}" ]]; then
  if [[ -x "$PYTHON_BIN" ]]; then
    :
  elif command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v "$PYTHON_BIN")"
  else
    echo "PYTHON_BIN is not executable: $PYTHON_BIN" >&2
    exit 1
  fi
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python)"
else
  echo "Python 3.10+ is required. Install Python or set PYTHON_BIN." >&2
  exit 1
fi

"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
  || { echo "Python 3.10+ is required; found $("$PYTHON_BIN" --version)." >&2; exit 1; }
"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
  || { echo "Python tests require Python 3.11+ because the platform uses datetime.UTC; found $("$PYTHON_BIN" --version)." >&2; exit 1; }
if ! "$PYTHON_BIN" -c 'import pytest, pytest_cov'; then
  echo "Python tests require test dependencies. Run: cd \"$ROOT\" && \"$PYTHON_BIN\" -m pip install -e \".[test]\"" >&2
  exit 1
fi

mkdir -p "$ROOT/build/test-results" "$ROOT/build/coverage"
cd "$ROOT"

args=(
  "$PYTHON_BIN" -m pytest
  "$ROOT/tests/python"
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
