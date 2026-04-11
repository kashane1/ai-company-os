#!/usr/bin/env bash
# Phase 1.2 — xcode preflight.
#
# Verifies xcodebuild and xcodegen are reachable, then regenerates the
# catchbook project.yml into a scratch copy to confirm the full chain works
# from a daemon context. Exits non-zero with a reason on failure; the
# runtime-supervisor marks the iOS lane `blocked` on failure.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${REPO_ROOT}/state/logs/runtime-supervisor"
mkdir -p "${LOG_DIR}"
LOG="${LOG_DIR}/preflight.log"

log() { printf '[xcode-preflight %s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "${LOG}"; }

if ! command -v xcodebuild >/dev/null 2>&1; then
  log "FAIL xcodebuild_not_on_path"
  exit 30
fi

if ! VERSION="$(xcodebuild -version 2>&1)"; then
  log "FAIL xcodebuild_version_failed: ${VERSION}"
  exit 31
fi
log "xcodebuild -version: ${VERSION//$'\n'/ | }"

if ! command -v xcodegen >/dev/null 2>&1; then
  log "FAIL xcodegen_not_on_path"
  exit 32
fi

PRODUCT_ROOT="${REPO_ROOT}/products/catchbook-ios"
if [[ ! -d "${PRODUCT_ROOT}" ]]; then
  log "SKIP catchbook-ios_not_present"
  exit 0
fi

SCRATCH="$(mktemp -d -t xcode-preflight-XXXX)"
trap 'rm -rf "${SCRATCH}"' EXIT
cp -R "${PRODUCT_ROOT}"/. "${SCRATCH}/"
if ! (cd "${SCRATCH}" && xcodegen generate --spec project.yml >/dev/null 2>&1); then
  log "FAIL xcodegen_generate_failed"
  exit 33
fi
log "xcodegen generate ok"

log "OK"
exit 0
