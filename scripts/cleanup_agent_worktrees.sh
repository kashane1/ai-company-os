#!/usr/bin/env bash
# Phase 0.2 — agent worktree hygiene.
#
# - Runs `git worktree prune` to drop .git/worktrees/ entries whose target
#   path no longer exists (git-native, safe).
# - Removes abandoned .claude/worktrees/<name> dirs older than 7 days, but
#   ONLY if they are clean and have no stashed work.
# - NEVER auto-removes an index.lock. If one is present, log and exit non-zero
#   so the founder can inspect.
#
# Intentionally on-demand only until run manually 3x without incident.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO_ROOT}"

LOCK="${REPO_ROOT}/.git/index.lock"
if [[ -f "${LOCK}" ]]; then
  echo "cleanup_agent_worktrees: ${LOCK} is present; refusing to proceed. Inspect before retrying." >&2
  exit 10
fi

echo "--> git worktree prune (verbose)"
git worktree prune --verbose

CLAUDE_WT_DIR="${REPO_ROOT}/.claude/worktrees"
if [[ -d "${CLAUDE_WT_DIR}" ]]; then
  echo "--> scanning ${CLAUDE_WT_DIR} for stale clean worktrees"
  find "${CLAUDE_WT_DIR}" -mindepth 1 -maxdepth 1 -type d -mtime +7 -print0 |
    while IFS= read -r -d '' dir; do
      if [[ ! -d "${dir}/.git" && ! -f "${dir}/.git" ]]; then
        echo "  skip (not a worktree): ${dir}"
        continue
      fi
      dirty="$(git -C "${dir}" status --porcelain 2>/dev/null || echo dirty)"
      stashed="$(git -C "${dir}" stash list 2>/dev/null || true)"
      if [[ -n "${dirty}" ]]; then
        echo "  skip (dirty): ${dir}"
        continue
      fi
      if [[ -n "${stashed}" ]]; then
        echo "  skip (has stash): ${dir}"
        continue
      fi
      echo "  removing stale clean worktree: ${dir}"
      git worktree remove --force "${dir}" || rm -rf "${dir}"
    done
fi

echo "cleanup_agent_worktrees: done"
