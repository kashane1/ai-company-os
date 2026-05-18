#!/usr/bin/env bash
# Zero-dependency end-to-end demo of the ai-company-os control loop.
# No Postgres, Redis, Codex, network, or Mac runtime required.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -x "${ROOT}/.venv/bin/python" ]; then
  PY="${ROOT}/.venv/bin/python"
else
  PY="$(command -v python3 || command -v python)"
fi

exec "${PY}" "${ROOT}/scripts/demo/run_demo.py" "$@"
