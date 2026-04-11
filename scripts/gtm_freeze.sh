#!/usr/bin/env bash
# Phase 2.0 — GTM lane kill switch.
# Writes state/flags/gtm_frozen. GTM worker checks on every claim and every
# MCP call. In-flight tasks are re-queued as paused:frozen.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FLAG="${REPO_ROOT}/state/flags/gtm_frozen"
mkdir -p "$(dirname "${FLAG}")"
REASON="${1:-manual freeze}"
printf 'frozen_at: %s\nreason: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${REASON}" >"${FLAG}"
echo "gtm: FROZEN (${FLAG})"
