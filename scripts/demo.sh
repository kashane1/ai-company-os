#!/usr/bin/env bash
# Zero-dependency fixture walkthrough of the ai-company-os control loop.
# No Postgres, Redis, Codex, network, or Mac runtime required.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -n "${PYTHON_BIN:-}" ]; then
  if [ -x "$PYTHON_BIN" ]; then
    PY="$PYTHON_BIN"
  elif command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    PY="$(command -v "$PYTHON_BIN")"
  else
    echo "PYTHON_BIN is not executable: $PYTHON_BIN" >&2
    exit 1
  fi
elif [ -x "${ROOT}/.venv/bin/python" ]; then
  PY="${ROOT}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PY="$(command -v python)"
else
  echo "Python 3.10+ is required. Install Python or set PYTHON_BIN." >&2
  exit 1
fi

"$PY" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
  || { echo "Python 3.10+ is required; found $("$PY" --version)." >&2; exit 1; }

exec "${PY}" "${ROOT}/scripts/demo/run_demo.py" "$@"
