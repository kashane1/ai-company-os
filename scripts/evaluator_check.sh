#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

RUN_FAST_TESTS=0
RUN_FULL_TESTS=0

usage() {
  cat <<'EOF'
Usage: ./scripts/evaluator_check.sh [--with-tests] [--full-tests]

Runs the zero-setup demo, verifies key evaluator-facing files exist, and checks
that the generated sample artifacts are parseable and structurally sane.

Options:
  --with-tests   Run a fast Python subset after the zero-setup checks.
  --full-tests   Run the full Python suite via ./scripts/test_python.sh.
  -h, --help     Show this help message.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-tests)
      RUN_FAST_TESTS=1
      ;;
    --full-tests)
      RUN_FULL_TESTS=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

if [[ "$RUN_FAST_TESTS" -eq 1 && "$RUN_FULL_TESTS" -eq 1 ]]; then
  echo "Choose either --with-tests or --full-tests, not both." >&2
  exit 1
fi

if [[ -x "$ROOT/.venv/bin/python3" ]]; then
  PYTHON_BIN="$ROOT/.venv/bin/python3"
else
  PYTHON_BIN="$(command -v python3 || command -v python)"
fi

echo "==> Running zero-setup demo"
"$ROOT/scripts/demo.sh"

echo
echo "==> Verifying evaluator-facing files"
required_paths=(
  "$ROOT/docs/FOR-EMPLOYERS.md"
  "$ROOT/docs/EVALUATOR-WALKTHROUGH.md"
  "$ROOT/docs/examples/README.md"
  "$ROOT/docs/examples/sample-task-run.json"
  "$ROOT/docs/examples/sample-approval.json"
  "$ROOT/docs/examples/sample-postmortem.json"
  "$ROOT/packages/policies/approvals.py"
  "$ROOT/packages/policies/approval_tokens.py"
  "$ROOT/apps/api/approval_endpoint.py"
  "$ROOT/scripts/scheduled/approval_sweep_session.md"
  "$ROOT/products/life-clock-ios/README.md"
  "$ROOT/products/catchbook-ios/README.md"
  "$ROOT/products/after-plans-ios/README.md"
)

for path in "${required_paths[@]}"; do
  if [[ ! -e "$path" ]]; then
    echo "Missing required path: $path" >&2
    exit 1
  fi
  echo "  ok  ${path#$ROOT/}"
done

echo
echo "==> Validating generated sample artifacts"
"$PYTHON_BIN" - <<'PY' "$ROOT"
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
examples = root / "docs" / "examples"

checks = {
    "sample-task-run.json": ["id", "task_id", "worker_lane", "status", "validation_checks"],
    "sample-approval.json": ["id", "status", "action", "subject_id"],
    "sample-postmortem.json": ["id", "failure_code", "lane", "status"],
}

for name, required_keys in checks.items():
    path = examples / name
    payload = json.loads(path.read_text())
    missing = [key for key in required_keys if key not in payload]
    if missing:
        raise SystemExit(f"{name} missing keys: {', '.join(missing)}")
    print(f"  ok  docs/examples/{name}")
PY

if [[ "$RUN_FAST_TESTS" -eq 1 ]]; then
  echo
  echo "==> Running fast Python verification subset"
  "$PYTHON_BIN" -m pytest \
    tests/python/integration/test_end_to_end_control_loop.py \
    tests/python/unit/test_typed_tool_surface.py \
    -q
elif [[ "$RUN_FULL_TESTS" -eq 1 ]]; then
  echo
  echo "==> Running full Python suite"
  "$ROOT/scripts/test_python.sh"
else
  echo
  echo "==> Skipping Python tests"
  echo "    Run ./scripts/evaluator_check.sh --with-tests for a fast subset"
  echo "    or ./scripts/evaluator_check.sh --full-tests for the full suite."
fi

echo
echo "Evaluator check passed."
