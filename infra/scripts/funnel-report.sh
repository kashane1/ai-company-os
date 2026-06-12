#!/usr/bin/env bash
# Scheduled funnel scoreboard refresh. Recomputes every prospect-to-client
# funnel stage from its primary source and rewrites state/prospects/funnel-report.{md,json}.
# Wired by infra/launchd/com.ai-company-os.funnel-report.plist.
#
# Usage:
#   infra/scripts/funnel-report.sh
#
# The operating metric of the company should be computed daily, not discovered
# in audits. The dashboard reads the JSON snapshot this writes.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "${REPO_ROOT}"

echo "[funnel-report] $(date -u +%FT%TZ) computing funnel scoreboard"
python3 scripts/agency/funnel_report.py
