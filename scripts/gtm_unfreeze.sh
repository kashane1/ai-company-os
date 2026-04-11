#!/usr/bin/env bash
# Phase 2.0 — clear the GTM kill switch.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FLAG="${REPO_ROOT}/state/flags/gtm_frozen"
if [[ -f "${FLAG}" ]]; then
  rm "${FLAG}"
  echo "gtm: UNFROZEN"
else
  echo "gtm: already clear"
fi
