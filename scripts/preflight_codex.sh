#!/usr/bin/env bash
# Phase 1.2 — codex preflight.
#
# Verifies the codex CLI is reachable and can run a trivial `codex exec` from
# a user-session daemon context. Exits 0 on success, non-zero with a reason on
# failure. The runtime-supervisor calls this at startup and marks the
# engineering lane `blocked` if it fails.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${REPO_ROOT}/state/logs/runtime-supervisor"
mkdir -p "${LOG_DIR}"
LOG="${LOG_DIR}/preflight.log"

log() { printf '[codex-preflight %s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "${LOG}"; }

if ! command -v codex >/dev/null 2>&1; then
  log "FAIL codex_not_on_path"
  exit 20
fi

if ! VERSION="$(codex --version 2>&1)"; then
  log "FAIL codex_version_failed: ${VERSION}"
  exit 21
fi
log "codex --version: ${VERSION}"

SCRATCH="$(mktemp -d -t codex-preflight-XXXX)"
trap 'rm -rf "${SCRATCH}"' EXIT
printf 'preflight scratch\n' >"${SCRATCH}/README.md"

if ! OUT="$(cd "${SCRATCH}" && codex exec --non-interactive --prompt 'Append a single line comment to README.md explaining its purpose.' 2>&1)"; then
  log "FAIL codex_exec_failed: ${OUT}"
  exit 22
fi
log "codex exec ok (${#OUT} bytes)"

log "OK"
exit 0
