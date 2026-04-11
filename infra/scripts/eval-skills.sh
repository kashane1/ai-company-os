#!/usr/bin/env bash
# Phase 0.5 — skill eval runner.
#
# Validator skills (kind: validator) are evaluated via pytest against their
# fixtures directory. Agentic skills (kind: agentic) are evaluated via
# promptfoo. This script enforces a --max-calls budget cap and rejects
# fixtures referencing production secret names.
#
# Usage:
#   infra/scripts/eval-skills.sh              # full sweep
#   infra/scripts/eval-skills.sh <skill-id>   # single skill
#   infra/scripts/eval-skills.sh --max-calls 9 <skill-id>
#
# Env:
#   EVAL_MAX_CALLS    Default 200 (nightly sweep); 9 per single-skill edit.
#   EVAL_PROVIDER     Promptfoo provider override (stub by default).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "${REPO_ROOT}"

MAX_CALLS="${EVAL_MAX_CALLS:-200}"
SKILL_FILTER=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-calls)
      MAX_CALLS="$2"
      shift 2
      ;;
    --help|-h)
      sed -n '2,20p' "$0"
      exit 0
      ;;
    *)
      SKILL_FILTER="$1"
      shift
      ;;
  esac
done

echo "eval-skills: max_calls=${MAX_CALLS} filter=${SKILL_FILTER:-<all>}"

# Lint: reject fixtures that reference production secret names.
FORBIDDEN='APP_STORE_CONNECT_API_KEY|BILLING_ADMIN_TOKEN|DNS_ADMIN_TOKEN|GITHUB_PROTECTED_BRANCH_TOKEN'
if grep -R --include='*.yaml' --include='*.yml' -l -E "\\\$ENV\\.(${FORBIDDEN})" skills/canonical/ 2>/dev/null; then
  echo "eval-skills: fixture references a production secret name; aborting." >&2
  exit 11
fi

# Node/promptfoo precheck (advisory — the runner degrades gracefully).
HAVE_PROMPTFOO=1
if ! command -v promptfoo >/dev/null 2>&1; then
  echo "eval-skills: promptfoo not on PATH. Install Node 20+ and promptfoo to run agentic evals."
  HAVE_PROMPTFOO=0
fi

CALLS_USED=0
FAIL=0

evaluate_skill() {
  local skill_dir="$1"
  local skill_id; skill_id="$(basename "${skill_dir}")"
  if [[ -n "${SKILL_FILTER}" && "${SKILL_FILTER}" != "${skill_id}" ]]; then
    return 0
  fi

  local fixtures="${skill_dir}/fixtures"
  if [[ ! -d "${fixtures}" ]]; then
    echo "  [${skill_id}] no fixtures/ dir — skipping (fixture_status=missing)."
    return 0
  fi

  if [[ -f "${skill_dir}/validator.py" ]]; then
    echo "  [${skill_id}] validator — pytest"
    if ! python3 -m pytest "${skill_dir}" -q 2>/dev/null; then
      echo "  [${skill_id}] validator pytest: FAIL"
      FAIL=$((FAIL + 1))
    fi
    return 0
  fi

  if [[ "${HAVE_PROMPTFOO}" != "1" ]]; then
    echo "  [${skill_id}] agentic — promptfoo missing, skipping (fixture_status unchanged)"
    return 0
  fi

  local budget=$((MAX_CALLS - CALLS_USED))
  if (( budget <= 0 )); then
    echo "  [${skill_id}] budget exhausted — skipping."
    return 0
  fi

  echo "  [${skill_id}] agentic — promptfoo (budget ${budget})"
  if ! promptfoo eval -c "${fixtures}/promptfooconfig.yaml" --max-concurrency 1 >/dev/null 2>&1; then
    echo "  [${skill_id}] agentic eval: FAIL"
    FAIL=$((FAIL + 1))
  fi
  CALLS_USED=$((CALLS_USED + 9))
}

echo "--> evaluating canonical skills"
for dir in skills/canonical/*/; do
  [[ -d "${dir}" ]] || continue
  evaluate_skill "${dir}"
done

if (( FAIL > 0 )); then
  echo "eval-skills: ${FAIL} skill(s) failed"
  exit 1
fi
echo "eval-skills: all evaluated skills passing (calls_used=${CALLS_USED})"
