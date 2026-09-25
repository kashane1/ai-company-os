#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

RUN_FAST_TESTS=0
RUN_FULL_TESTS=0

usage() {
  cat <<'EOF'
Usage: ./scripts/evaluator_check.sh [--with-tests] [--full-tests]

Runs a zero-setup fixture walkthrough, verifies key evaluator-facing files,
deserializes generated samples through their real schemas, and checks local
Markdown links in the employer path. It does not execute an agent or request
an approval.

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

select_python() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    if [[ -x "$PYTHON_BIN" ]]; then
      printf '%s\n' "$PYTHON_BIN"
      return
    fi
    if command -v "$PYTHON_BIN" >/dev/null 2>&1; then
      command -v "$PYTHON_BIN"
      return
    fi
    echo "PYTHON_BIN is not executable: $PYTHON_BIN" >&2
    exit 1
  fi
  if [[ -x "$ROOT/.venv/bin/python" ]]; then
    printf '%s\n' "$ROOT/.venv/bin/python"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return
  fi
  echo "Python 3.10+ is required. Install Python or set PYTHON_BIN." >&2
  exit 1
}

PYTHON_BIN="$(select_python)"
export PYTHON_BIN
"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
  || { echo "Python 3.10+ is required; found $("$PYTHON_BIN" --version)." >&2; exit 1; }

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
echo "==> Validating checked-in samples and evaluator links"
"$PYTHON_BIN" "$ROOT/scripts/evaluator_validation.py" "$ROOT"

echo
echo "==> Running zero-setup fixture walkthrough"
"$ROOT/scripts/demo.sh"

echo
echo "==> Revalidating regenerated samples"
"$PYTHON_BIN" "$ROOT/scripts/evaluator_validation.py" "$ROOT"

if [[ "$RUN_FAST_TESTS" -eq 1 ]]; then
  echo
  echo "==> Running fast Python verification subset"
  "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
    || { echo "Fast checks require Python 3.11+ because the approval/API path uses datetime.UTC; found $("$PYTHON_BIN" --version)." >&2; exit 1; }
  if ! "$PYTHON_BIN" -c 'import fastapi, httpx, multipart, pytest'; then
    echo "Fast checks require test dependencies. Run: cd \"$ROOT\" && \"$PYTHON_BIN\" -m pip install -e \".[test]\"" >&2
    exit 1
  fi
  cd "$ROOT"
  "$PYTHON_BIN" -m pytest \
    "$ROOT/tests/python/integration/test_end_to_end_control_loop.py" \
    "$ROOT/tests/python/integration/test_approval_tokens.py" \
    "$ROOT/tests/python/integration/test_audit_artifact_crash_safety.py" \
    "$ROOT/tests/python/unit/test_approvals.py" \
    "$ROOT/tests/python/unit/test_typed_tool_surface.py" \
    -q
elif [[ "$RUN_FULL_TESTS" -eq 1 ]]; then
  echo
  echo "==> Running full Python suite"
  "$ROOT/scripts/test_python.sh"
else
  echo
  echo "==> Skipping Python tests"
  echo "    Run ./scripts/evaluator_check.sh --with-tests for approval and schema checks"
  echo "    or ./scripts/evaluator_check.sh --full-tests for the full suite."
fi

echo
echo "Evaluator check passed."
