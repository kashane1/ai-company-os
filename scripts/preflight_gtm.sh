#!/usr/bin/env bash
# Phase 2.2 — GTM preflight.
#
# Verifies Postiz and Gemini credentials resolve (via the secrets helper),
# checks the threat-model acknowledgment, and fails loud if the kill switch
# is engaged. Safe to run from a daemon context.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${REPO_ROOT}/state/logs/runtime-supervisor"
mkdir -p "${LOG_DIR}"
LOG="${LOG_DIR}/preflight.log"
log() { printf '[gtm-preflight %s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "${LOG}"; }

cd "${REPO_ROOT}"

if [[ -f "${REPO_ROOT}/state/flags/gtm_frozen" ]]; then
  log "FAIL gtm_frozen"
  exit 40
fi

python3 - <<'PY'
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from packages.config import secrets

root = Path.cwd()
errors = []
if not secrets.get_secret("POSTIZ_API_KEY"):
    errors.append("POSTIZ_API_KEY missing")
if not secrets.get_secret("GEMINI_API_KEY"):
    errors.append("GEMINI_API_KEY missing")

tm = root / "docs/security/mcp-threat-model.md"
state = root / "state/checkpoints/platform/security-state.json"
if not tm.exists():
    errors.append("threat model missing")
elif not state.exists():
    errors.append("threat model unacknowledged")
else:
    payload = json.loads(state.read_text())
    recorded = (payload.get("mcp-threat-model") or {}).get("checksum")
    actual = hashlib.sha256(tm.read_bytes()).hexdigest()
    if not recorded:
        errors.append("threat model unacknowledged")
    elif recorded != actual:
        errors.append("threat model drift — run scripts/acknowledge_threat_model.sh --read")

if errors:
    for e in errors:
        print(f"FAIL {e}")
    sys.exit(41)
print("gtm secrets and threat model: OK")
PY

log "OK"
exit 0
