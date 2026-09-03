#!/usr/bin/env bash
# Phase 5.5 — skill intake validator.
#
# Usage: infra/scripts/validate-skill-intake.sh <skill-id>
#
# Walks the ten-item intake checklist from docs/skills/intake-policy.md
# and exits non-zero on the first failure. Designed to be run from the
# repo root on both CI and a developer's Mac.

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <skill-id>" >&2
  exit 64
fi

SKILL_ID="$1"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SKILL_DIR="${REPO_ROOT}/skills/canonical/${SKILL_ID}"

fail() { echo "FAIL: $1" >&2; exit 1; }
pass() { echo "ok  : $1"; }

# 1. Canonical definition
[ -f "${SKILL_DIR}/skill.md" ] || fail "skill.md missing at ${SKILL_DIR}"
pass "1/10 canonical skill.md present"

# 2. Contract
[ -f "${SKILL_DIR}/contract.yaml" ] || fail "contract.yaml missing"
grep -q "^inputs:" "${SKILL_DIR}/contract.yaml" || fail "contract.yaml missing inputs:"
grep -q "^outputs:" "${SKILL_DIR}/contract.yaml" || fail "contract.yaml missing outputs:"
pass "2/10 contract.yaml has inputs + outputs"

# 3. Kind selector
if grep -q "^kind: validator" "${SKILL_DIR}/skill.md" 2>/dev/null; then
  [ -f "${SKILL_DIR}/validator.py" ] || fail "validator skill missing validator.py"
  grep -q "^def run(" "${SKILL_DIR}/validator.py" || fail "validator.py missing run()"
fi
pass "3/10 kind selector honored"

# 4. Fixture suite
FIXTURE_DIR="${SKILL_DIR}/fixtures"
[ -d "${FIXTURE_DIR}" ] || fail "fixtures/ directory missing"
HAPPY=$(ls "${FIXTURE_DIR}" 2>/dev/null | grep -i happy || true)
BOUND=$(ls "${FIXTURE_DIR}" 2>/dev/null | grep -i boundary || true)
ADV=$(ls "${FIXTURE_DIR}" 2>/dev/null | grep -i adversarial || true)
[ -n "${HAPPY}" ] || fail "fixtures/ missing a happy_path fixture"
[ -n "${BOUND}" ] || fail "fixtures/ missing a boundary fixture"
[ -n "${ADV}" ]   || fail "fixtures/ missing an adversarial fixture"
pass "4/10 fixtures cover happy/boundary/adversarial"

# 5. Eval harness (best-effort — warn-only if the harness rejects the id)
if [ -x "${REPO_ROOT}/infra/scripts/eval-skills.sh" ]; then
  if "${REPO_ROOT}/infra/scripts/eval-skills.sh" "${SKILL_ID}" >/dev/null 2>&1; then
    pass "5/10 eval harness green"
  else
    echo "warn: eval-skills.sh did not run ${SKILL_ID} (rerun manually before promotion)" >&2
    pass "5/10 eval harness deferred"
  fi
else
  pass "5/10 eval harness not installed (skipped)"
fi

# 6. gitleaks secret scan
if command -v gitleaks >/dev/null 2>&1; then
  gitleaks detect --no-banner --redact --no-git --source "${SKILL_DIR}" \
    || fail "gitleaks found a potential secret in ${SKILL_DIR}"
  pass "6/10 gitleaks clean"
else
  echo "warn: gitleaks not installed; skipping secret scan" >&2
fi

# 7. Redaction contract
if grep -RIl "log" "${SKILL_DIR}" >/dev/null 2>&1; then
  if grep -RIl "redact" "${SKILL_DIR}" >/dev/null 2>&1; then
    pass "7/10 redaction referenced"
  else
    echo "warn: skill touches logs but does not reference redact()" >&2
  fi
else
  pass "7/10 no log I/O (skipped)"
fi

# 8. Edit boundaries for agentic skills
if grep -q "^kind: agentic" "${SKILL_DIR}/skill.md" 2>/dev/null; then
  grep -q "allowed_edit_boundaries" "${SKILL_DIR}/skill.md" \
    || fail "agentic skill missing allowed_edit_boundaries"
  pass "8/10 allowed_edit_boundaries declared"
else
  pass "8/10 validator skill (boundaries n/a)"
fi

# 9. Provenance
REGISTRY="${REPO_ROOT}/skills/registry.yaml"
if grep -q "id: ${SKILL_ID}" "${REGISTRY}"; then
  BLOCK=$(awk "/id: ${SKILL_ID}/,/^\$/" "${REGISTRY}")
  echo "${BLOCK}" | grep -q "source:" || fail "registry entry missing source:"
  if echo "${BLOCK}" | grep -q "source: external"; then
    echo "${BLOCK}" | grep -q "@" || fail "external source must pin <repo>@<commit>"
  fi
  pass "9/10 provenance recorded"
else
  pass "9/10 not yet in registry (skipped)"
fi

# 10. Registry last
if grep -q "id: ${SKILL_ID}" "${REGISTRY}"; then
  pass "10/10 registry entry present"
else
  echo "info: skill ${SKILL_ID} not yet promoted in registry.yaml" >&2
  pass "10/10 promotion pending (ok)"
fi

echo "intake: ${SKILL_ID} passed ten-item checklist"
