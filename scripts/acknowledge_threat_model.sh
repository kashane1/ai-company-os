#!/usr/bin/env bash
# Phase 2.0 — re-acknowledge the MCP threat model.
#
# Usage:
#   scripts/acknowledge_threat_model.sh --read
#
# The --read flag is a lightweight "I actually reviewed the diff" gesture.
# Without it the script refuses to update the recorded checksum.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ "${1:-}" != "--read" ]]; then
  echo "usage: acknowledge_threat_model.sh --read  (review the diff first)" >&2
  exit 1
fi

TM="${REPO_ROOT}/docs/security/mcp-threat-model.md"
if [[ ! -f "${TM}" ]]; then
  echo "threat model not found at ${TM}" >&2
  exit 2
fi

NEW_SHA="$(shasum -a 256 "${TM}" | awk '{print $1}')"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
STATE_DIR="${REPO_ROOT}/state/checkpoints/platform"
STATE_FILE="${STATE_DIR}/security-state.json"
LOG_FILE="${STATE_DIR}/security-log.jsonl"
mkdir -p "${STATE_DIR}"

OLD_SHA="none"
if [[ -f "${STATE_FILE}" ]]; then
  OLD_SHA="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("mcp-threat-model",{}).get("checksum","none"))' "${STATE_FILE}" 2>/dev/null || echo none)"
fi

python3 -c "
import json, os, sys
path = sys.argv[1]
payload = {}
if os.path.exists(path):
    try: payload = json.load(open(path))
    except Exception: payload = {}
payload['mcp-threat-model'] = {'checksum': sys.argv[2], 'acknowledged_at': sys.argv[3]}
open(path,'w').write(json.dumps(payload, indent=2, sort_keys=True))
" "${STATE_FILE}" "${NEW_SHA}" "${TS}"

printf '{"ts":"%s","file":"docs/security/mcp-threat-model.md","old_sha":"%s","new_sha":"%s","actor":"%s"}\n' \
  "${TS}" "${OLD_SHA}" "${NEW_SHA}" "${USER:-unknown}" >>"${LOG_FILE}"

echo "acknowledged ${NEW_SHA}"
