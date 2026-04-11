#!/usr/bin/env bash
# Phase 0.0 — filesystem round-trip handshake.
#
# Reads the newest .ping file under state/handshake/ and writes a matching
# .pong file with the same basename. Claude (sandbox side) then asserts the
# pong exists with matching content and sub-second visibility.
#
# Usage:
#   scripts/handshake_echo.sh            # echo the newest .ping
#   scripts/handshake_echo.sh <ping>     # echo a specific .ping file
#
# Failure modes it surfaces:
#   - No ping found                  -> exit 2
#   - Ping unreadable / encoding bad -> exit 3
#   - Pong write failed              -> exit 4

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HANDSHAKE_DIR="${REPO_ROOT}/state/handshake"

mkdir -p "${HANDSHAKE_DIR}"

if [[ $# -ge 1 ]]; then
  PING="$1"
else
  PING="$(ls -1t "${HANDSHAKE_DIR}"/claude-*.ping 2>/dev/null | head -n1 || true)"
fi

if [[ -z "${PING:-}" || ! -f "${PING}" ]]; then
  echo "handshake: no ping file found under ${HANDSHAKE_DIR}" >&2
  exit 2
fi

if ! CONTENT="$(LC_ALL=C.UTF-8 cat "${PING}")"; then
  echo "handshake: failed to read ${PING}" >&2
  exit 3
fi

BASE="$(basename "${PING}" .ping)"
PONG="${HANDSHAKE_DIR}/${BASE}.pong"
MAC_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

{
  printf 'pong-of: %s\n' "${BASE}"
  printf 'mac-timestamp: %s\n' "${MAC_TS}"
  printf '%s\n' '---'
  printf '%s\n' "${CONTENT}"
} >"${PONG}.tmp"

mv "${PONG}.tmp" "${PONG}"
echo "wrote ${PONG}"
